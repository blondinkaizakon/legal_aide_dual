from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from core.config import TOKEN
from core.pdf_tool import extract_text
from core.analyzer import analyze
from core.doc_generator import build
from core.kb_search import find_answer
import pickle
import tempfile
import os
import logging
# --- Импорты для векторной базы знаний ---
from sentence_transformers import SentenceTransformer
import faiss
# --- Конец импортов ---

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Загрузка векторной базы знаний ---
logger.info("Загрузка модели NLP...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

logger.info("Загрузка FAISS индекса...")
index = faiss.read_index("data/faiss_index.bin")

logger.info("Загрузка метаданных...")
with open("data/kb_metadata.pkl", "rb") as f:
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
        if 0 <= idx < len(metadata_list) and score >= threshold:
            results.append({
                "metadata": metadata_list[idx],
                "score": float(score)
            })
    return results
# --- Конец функции поиска ---

API_TOKEN = TOKEN
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Состояния пользователей
user_states = {} # {user_id: {'state': str, 'data': dict}}

# Константы состояний
STATE_START = "start"
STATE_WAITING_QUESTION = "waiting_question"
STATE_WAITING_DOC_TYPE = "waiting_doc_type"
STATE_WAITING_DOC_DATA = "waiting_doc_data" # Общее состояние для сбора данных договора
STATE_WAITING_DOC_UPLOAD = "waiting_doc_upload" # Состояние ожидания документа для анализа

# Типы документов для генерации
DOC_TYPES = {
    "Договор работы": "work_contract",
    "Договор услуги": "service_contract",
    "Договор поставки": "supply_contract",
    "Трудовой договор": "employment_contract",
    "Дополнительное соглашение": "addendum",
    "Соглашение о расторжении": "termination_agreement",
    "Претензия": "claim",
}

@dp.message_handler(commands="start")
async def start(m: types.Message):
    user_id = m.from_user.id
    logger.info(f"Пользователь {user_id} нажал /start. Сбрасываю состояние.")
    # Сбрасываем состояние при /start
    user_states[user_id] = {'state': STATE_START, 'data': {}}
    logger.info(f"Состояние пользователя {user_id} сброшено до {STATE_START}.")
    
    # Создаём главное меню
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("❓ Задать вопрос")
    kb.add("📄 Получить готовый документ")
    kb.add("🔍 Распознать документ")
    
    await m.answer("Ваш юридический помощник приветствует вас! Чем могу помочь?", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "❓ Задать вопрос")
async def ask_question(m: types.Message):
    user_id = m.from_user.id
    logger.info(f"Пользователь {user_id} нажал '❓ Задать вопрос'. Устанавливаю состояние {STATE_WAITING_QUESTION}.")
    user_states[user_id]['state'] = STATE_WAITING_QUESTION
    await m.answer("Напишите ваш вопрос:")

@dp.message_handler(lambda m: m.text == "📄 Получить готовый документ")
async def choose_document_type(m: types.Message):
    user_id = m.from_user.id
    logger.info(f"Пользователь {user_id} нажал '📄 Получить готовый документ'. Устанавливаю состояние {STATE_WAITING_DOC_TYPE}.")
    user_states[user_id]['state'] = STATE_WAITING_DOC_TYPE
    
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for doc_type in DOC_TYPES.keys():
        kb.add(doc_type)
    kb.add("Назад")
    
    await m.answer("Выберите тип документа:", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "🔍 Распознать документ")
async def request_document(m: types.Message):
    user_id = m.from_user.id
    logger.info(f"Пользователь {user_id} нажал '🔍 Распознать документ'. Устанавливаю состояние {STATE_WAITING_DOC_UPLOAD}.")
    user_states[user_id]['state'] = STATE_WAITING_DOC_UPLOAD
    await m.answer("Пришлите PDF-файл или фото документа для анализа.")

# --- ОБРАБОТЧИКИ КОНТЕНТА (ФАЙЛЫ, ФОТО) ---
# Обработчик для PDF
@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def handle_uploaded_document(m: types.Message):
    user_id = m.from_user.id
    state_info = user_states.get(user_id, {'state': STATE_START})
    logger.info(f"Пользователь {user_id} прислал PDF. Текущее состояние: {state_info['state']}")

    if state_info['state'] == STATE_WAITING_DOC_UPLOAD:
        if not m.document.file_name.lower().endswith(".pdf"):
            await m.reply("Пожалуйста, пришлите документ в формате PDF.")
            return

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            await m.document.download(tmp.name)
            try:
                # Извлечение текста из PDF
                text = extract_text(tmp.name)
                # Анализ текста (предполагается, что analyze возвращает список рисков/выводов)
                analysis_result = "\n".join(analyze(text))
                await m.answer(f"Результаты анализа документа:\n\n{analysis_result}")
            except Exception as e:
                logger.error(f"Ошибка при обработке документа: {e}")
                await m.answer("Произошла ошибка при обработке документа.")
            finally:
                os.unlink(tmp.name)
        
        # Возврат в начальное состояние после анализа
        user_states[user_id] = {'state': STATE_START, 'data': {}}
        logger.info(f"Состояние пользователя {user_id} после анализа PDF сброшено до {STATE_START}.")
    else:
        await m.answer("Сначала выберите 'Распознать документ' из меню.")

# Обработчик для фото
@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_uploaded_photo(m: types.Message):
    user_id = m.from_user.id
    state_info = user_states.get(user_id, {'state': STATE_START})
    logger.info(f"Пользователь {user_id} прислал фото. Текущее состояние: {state_info['state']}")

    if state_info['state'] == STATE_WAITING_DOC_UPLOAD:
        # Получаем file_id самого большого размера (наивысшее качество)
        photo = m.photo[-1]
        file_id = photo.file_id
        
        # Скачиваем фото
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path
        
        # Создаём временное изображение
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_img:
            await bot.download_file(file_path, tmp_img.name)
            # Здесь должна быть логика OCR и последующего анализа
            # Пока что просто сообщение
            await m.answer("Фото документа получено. Обработка изображения (OCR) и анализ пока не реализованы в этом примере.")
            os.unlink(tmp_img.name)

        # Возврат в начальное состояние после анализа
        user_states[user_id] = {'state': STATE_START, 'data': {}}
        logger.info(f"Состояние пользователя {user_id} после анализа фото сброшено до {STATE_START}.")
    else:
        await m.answer("Сначала выберите 'Распознать документ' из меню.")

# --- ОБЩИЙ ОБРАБОТЧИК СООБЩЕНИЙ (ДОЛЖЕН БЫТЬ ПОСЛЕДНИМ) ---
@dp.message_handler()
async def handle_message(m: types.Message):
    user_id = m.from_user.id
    text = m.text.strip()
    state_info = user_states.get(user_id, {'state': STATE_START, 'data': {}})
    state = state_info['state']
    data = state_info['data']
    logger.info(f"Пользователь {user_id} отправил сообщение '{text}'. Текущее состояние: {state}")

    if state == STATE_WAITING_QUESTION:
        logger.info(f"Поиск в KB для пользователя {user_id}: {text}")
        kb_results = search_in_knowledge_base(text, top_k=1, threshold=0.6)

        if kb_results:
            best_match = kb_results[0]
            source_file = best_match['metadata'].get('source_file', 'Неизвестный документ')
            chunk_text = best_match['metadata'].get('original_chunk', '')[:500] + "..." # Обрезаем для вывода
            score = best_match['score']
            response_text = f"Найдено в документе '{source_file}' (схожесть: {score:.2f}):\n\n{chunk_text}"
        else:
            # Резервный поиск
            logger.info(f"Ответ не найден в векторной базе. Использую find_answer для '{text}'.")
            fallback_answer = find_answer(text)
            response_text = fallback_answer # find_answer должен возвращать строку

        await m.answer(response_text)
        # Возврат в начальное состояние после ответа на вопрос
        user_states[user_id] = {'state': STATE_START, 'data': {}}
        logger.info(f"Состояние пользователя {user_id} после ответа на вопрос сброшено до {STATE_START}.")

    elif state == STATE_WAITING_DOC_TYPE:
        if text in DOC_TYPES:
            data['doc_type'] = DOC_TYPES[text]
            data['doc_data'] = {} # Инициализируем словарь для данных договора
            data['doc_data']['step'] = 'client' # Устанавливаем первый шаг
            user_states[user_id]['state'] = STATE_WAITING_DOC_DATA
            logger.info(f"Пользователь {user_id} выбрал тип документа '{text}'. Устанавливаю состояние {STATE_WAITING_DOC_DATA}.")
            await m.answer(f"Вы выбрали '{text}'. Кто заказчик/покупатель/работодатель?")
        elif text == "Назад":
            user_states[user_id] = {'state': STATE_START, 'data': {}}
            logger.info(f"Пользователь {user_id} нажал 'Назад'. Возврат в {STATE_START}.")
            await start(m) # Повторно отправляем стартовое сообщение и меню
        else:
            await m.answer("Пожалуйста, выберите тип документа из меню.")

    elif state == STATE_WAITING_DOC_DATA:
        # Собираем данные для договора
        step = data['doc_data'].get('step')
        logger.info(f"Сбор данных для договора. Шаг: {step}")
        if step == 'client':
            data['doc_data']['client'] = text
            data['doc_data']['step'] = 'contractor'
            await m.answer("Кто исполнитель/поставщик/работник?")
        elif step == 'contractor':
            data['doc_data']['contractor'] = text
            data['doc_data']['step'] = 'subject'
            await m.answer("О чём договор/соглашение?")
        elif step == 'subject':
            data['doc_data']['subject'] = text
            data['doc_data']['step'] = 'price'
            await m.answer("Цена договора?")
        elif step == 'price':
            data['doc_data']['price'] = text
            data['doc_data']['step'] = 'term'
            await m.answer("Срок действия договора?")
        elif step == 'term':
            data['doc_data']['term'] = text
            # Все данные собраны
            # Генерируем документ (псевдокод, замените на реальную логику)
            # doc_content = generate_document(data['doc_type'], data['doc_data'])
            # await m.answer_document(doc_content) # Отправка файла
            await m.answer(f"Данные для '{data['doc_type']}' собраны. (Документ генерируется...)\n\n"
                           f"Заказчик: {data['doc_data']['client']}\n"
                           f"Исполнитель: {data['doc_data']['contractor']}\n"
                           f"Предмет: {data['doc_data']['subject']}\n"
                           f"Цена: {data['doc_data']['price']}\n"
                           f"Срок: {data['doc_data']['term']}")
            
            # Возврат в начальное состояние после генерации
            user_states[user_id] = {'state': STATE_START, 'data': {}}
            logger.info(f"Состояние пользователя {user_id} после сбора данных сброшено до {STATE_START}.")
        else:
            # Непредвиденное состояние
            await m.answer("Произошла ошибка при сборе данных. Пожалуйста, начните снова.")
            user_states[user_id] = {'state': STATE_START, 'data': {}}
            logger.info(f"Состояние пользователя {user_id} после ошибки сброшено до {STATE_START}.")

    elif state == STATE_START:
        # Если пользователь что-то ввёл в начальном состоянии, не нажав кнопку
        logger.info(f"Пользователь {user_id} ввел текст в состоянии {STATE_START}, не нажав кнопку.")
        await m.answer("Пожалуйста, воспользуйтесь меню.")

    else:
        # Любое другое неожиданное состояние
        logger.warning(f"Пользователь {user_id} в неожиданном состоянии: {state}")
        await m.answer("Произошла ошибка. Пожалуйста, используйте команду /start.")
        user_states[user_id] = {'state': STATE_START, 'data': {}}
        logger.info(f"Состояние пользователя {user_id} после ошибки сброшено до {STATE_START}.")


if __name__ == "__main__":
    logger.info("Запускаю бота...")
    executor.start_polling(dp, skip_updates=True)
