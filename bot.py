# bot.py
import pickle # Для загрузки метаданных
from sentence_transformers import SentenceTransformer # Для NLP
import faiss # Для векторной базы
import os # Для работы с путями
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from core.config import TOKEN
from core.pdf_tool import extract_text
from core.analyzer import analyze
from core.doc_generator import build
from core.kb_search import find_answer
import pickle

logger.info("Загрузка модели NLP...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

logger.info("Загрузка FAISS индекса...")
index = faiss.read_index("faiss_index.bin")

logger.info("Загрузка метаданных...")
with open("metadata.pkl", "rb") as f:
    metadata_list = pickle.load(f)

logger.info("Модель, индекс и метаданные загружены.")
API_TOKEN = TOKEN
bot = Bot(token=API_TOKEN)
dp  = Dispatcher(bot)

user_data = {}   # {user_id: dict}

@dp.message_handler(commands="start")
async def start(m: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📄 Анализ PDF", "📝 Создать договор", "❓ Задать вопрос")
    await m.answer("👋 LegalAideIPbot – помощник для ИП", reply_markup=kb)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (проверки согласия, состояний, команд) ...

    if state == STATE_START:
        # ... (проверки юмора, кнопок меню) ...
        # Если не подошло ни одно из специфических условий
        user_question = update.message.text.strip()
        # Вызов поиска в базе знаний
        kb_results = search_in_knowledge_base(user_question, top_k=1)

        if kb_results and kb_results[0]['score'] > 0.5: # Порог сходства
            best_match = kb_results[0]
            source_file = best_match['metadata'].get('source_file', 'Неизвестный документ')
            chunk_text = best_match['metadata'].get('original_chunk', '')[:500] + "..." # Обрезаем для вывода
            response_text = f"Найдено в документе '{source_file}':\n\n{chunk_text}\n\nОценка сходства: {best_match['score']:.4f}"
        else:
            # Если не найдено в базе знаний, используйте старую логику или стандартный ответ
            response_text = TEXTS["unknown_message"] # или другая логика

        await update.message.reply_text(
            response_text,
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True)
        )
        # USER_STATES[user_id] = STATE_START # Уже в START
   
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

@dp.message_handler(lambda m: m.text == "📝 Создать договор")
async def new_contract(m: types.Message):
    user_data[m.from_user.id] = {}
    await m.answer("Введите город (например, Москва):")

@dp.message_handler(lambda m: m.text == "❓ Задать вопрос")
async def ask(m: types.Message):
    await m.answer("Напишите ваш вопрос:")

@dp.message_handler()
async def collect(m: types.Message):
    uid = m.from_user.id
    data = user_data.setdefault(uid, {})
    if "city" not in data:
        data["city"] = m.text
        return await m.answer("Арендодатель (ФИО полностью):")
    if "landlord" not in data:
        data["landlord"] = m.text
        return await m.answer("Арендатор (ФИО полностью):")
    if "tenant" not in data:
        data["tenant"] = m.text
        return await m.answer("Описание помещения (адрес, площадь):")
    if "property" not in data:
        data["property"] = m.text
        return await m.answer("Сумма аренды в месяц (руб.):")
    if "rent" not in data:
        data["rent"] = m.text
        data.update({"day": "01", "month": "января", "year": "2025",
                     "landlord_passport": "серия 1234 №567890",
                     "tenant_passport":  "серия 9876 №543210"})
        out_path = build(data, f"аренда_ИП_{uid}.docx")
        await m.reply_document(types.InputFile(out_path))
        data.clear()
    else:
        await m.answer(find_answer(m.text))

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

def search_in_knowledge_base(query_text, top_k=1):
    """Поиск в векторной базе знаний."""
    query_embedding = model.encode([query_text])
    faiss.normalize_L2(query_embedding.astype('float32'))
    scores, indices = index.search(query_embedding.astype('float32'), top_k)

    results = []
    for i in range(len(indices[0])):
        idx = indices[0][i]
        if 0 <= idx < len(metadata_list): # Проверка границ
            results.append({
                "metadata": metadata_list[idx],
                "score": scores[0][i]
            })
    return results
