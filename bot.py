from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from core.config import TOKEN
from core.pdf_tool import extract_text
from core.analyzer import analyze
from core.doc_generator import build
from core.kb_search import find_answer # Оставляем, если используется для других целей
import pickle
import tempfile
import os
# --- Импорты для векторной базы знаний ---
from sentence_transformers import SentenceTransformer
import faiss
# --- Конец импортов ---

# --- Загрузка векторной базы знаний ---
logger.info("Загрузка модели NLP...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

logger.info("Загрузка FAISS индекса...")
index = faiss.read_index("faiss_index.bin")

logger.info("Загрузка метаданных...")
with open("metadata.pkl", "rb") as f:
    metadata_list = pickle.load(f)

logger.info("Модель, индекс и метаданные загружены.")

# --- Функция поиска в базе знаний ---
def search_in_knowledge_base(query_text, top_k=1, threshold=0.5):
    """Поиск в векторной базе знаний."""
    if not query_text.strip():
        return []
    query_embedding = model.encode([query_text])
    faiss.normalize_L2(query_embedding.astype('float32'))
    scores, indices = index.search(query_embedding.astype('float32'), top_k)

    results = []
    for i in range(len(indices[0])):
        idx = indices[0][i]
        score = scores[0][i]
        if 0 <= idx < len(metadata_list) and score >= threshold: # Проверка границ и порога
            results.append({
                "metadata": metadata_list[idx],
                "score": float(score) # Преобразуем в float для JSON-совместимости, если нужно
            })
    return results
# --- Конец функции поиска ---

API_TOKEN = TOKEN
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_data = {}   # {user_id: dict}

@dp.message_handler(commands="start")
async def start(m: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📄 Анализ PDF", "📝 Создать договор", "❓ Задать вопрос")
    await m.answer("👋 LegalAideIPbot – помощник для ИП", reply_markup=kb)

# Обработчик для PDF
@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def handle_doc(m: types.Message):
    if not m.document.file_name.lower().endswith(".pdf"):
        return await m.reply("Пришлите PDF-договор")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        await m.document.download(tmp.name)
        text = extract_text(tmp.name)
        os.unlink(tmp.name)
        risks = "\n".join(analyze(text))
        await m.answer(risks)

# Обработчик для кнопки "Создать договор"
@dp.message_handler(lambda m: m.text == "📝 Создать договор")
async def new_contract(m: types.Message):
    user_data[m.from_user.id] = {}
    await m.answer("Введите город (например, Москва):")

# Обработчик для кнопки "Задать вопрос"
@dp.message_handler(lambda m: m.text == "❓ Задать вопрос")
async def ask(m: types.Message):
    await m.answer("Напишите ваш вопрос:")

# Общий обработчик сообщений
@dp.message_handler()
async def collect(m: types.Message):
    uid = m.from_user.id
    text = m.text.strip()
    data = user_data.setdefault(uid, {})

    # --- НОВОЕ: Поиск в векторной базе знаний ---
    # Проверяем, не находится ли пользователь в процессе заполнения данных для договора
    # Если ключи "city", "landlord", "tenant", "property", "rent" отсутствуют в data,
    # значит, пользователь не находится в процессе создания договора.
    # Также можно добавить проверку, что текст не пустой и не является командой.
    if not data: # Если словарь пуст, пользователь не начал создание договора
        kb_results = search_in_knowledge_base(text, top_k=1, threshold=0.6) # Порог можно настроить

        if kb_results:
            best_match = kb_results[0]
            source_file = best_match['metadata'].get('source_file', 'Неизвестный документ')
            chunk_text = best_match['metadata'].get('original_chunk', '')[:500] + "..." # Обрезаем для вывода
            score = best_match['score']
            response_text = f"Найдено в документе '{source_file}' (схожесть: {score:.2f}):\n\n{chunk_text}"
            await m.answer(response_text)
            return # Выходим, чтобы не продолжать другие проверки после нахождения в KB
        # Если в KB не найдено, можно либо ничего не делать, либо использовать find_answer
        # else:
        #     # Если find_answer возвращает что-то осмысленное, можно использовать его
        #     fallback_answer = find_answer(text)
        #     if fallback_answer != "Ответ не найден": # Предполагаем, что find_answer возвращает "Ответ не найден"
        #         await m.answer(fallback_answer)
        #     # Или просто игнорируем и ждем следующего сообщения
    # --- КОНЕЦ НОВОГО ---

    # --- Старая логика для создания договора ---
    if "city" not in data:
        data["city"] = text
        return await m.answer("Арендодатель (ФИО полностью):")
    if "landlord" not in data:
        data["landlord"] = text
        return await m.answer("Арендатор (ФИО полностью):")
    if "tenant" not in data:
        data["tenant"] = text
        return await m.answer("Описание помещения (адрес, площадь):")
    if "property" not in data:
        data["property"] = text
        return await m.answer("Сумма аренды в месяц (руб.):")
    if "rent" not in data:
        data["rent"] = text
        data.update({"day": "01", "month": "января", "year": "2025",
                     "landlord_passport": "серия 1234 №567890",
                     "tenant_passport":  "серия 9876 №543210"})
        out_path = build(data, f"аренда_ИП_{uid}.docx")
        await m.reply_document(types.InputFile(out_path))
        data.clear()
    # --- Конец старой логики ---
    else:
        # Этот else срабатывает, если пользователь не в процессе создания договора
        # и не нашлось ничего в векторной базе знаний (или если порог не был пройден).
        # Можно использовать find_answer как резервный вариант.
        fallback_answer = find_answer(text)
        await m.answer(fallback_answer)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

# Функция search_in_knowledge_base уже определена выше
