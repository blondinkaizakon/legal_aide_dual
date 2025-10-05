import asyncio, tempfile, os
from aiogram import Bot, Dispatcher, types
import asyncio
async def main():
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())
from core.config import TOKEN
from core.pdf_tool import extract_text
from core.analyzer import analyze
from core.doc_generator import build
from core.kb_search import find_answer

API_TOKEN = "8440749347:AAFeXggvdBjedsTHI9cOHrHvG6vUrBnka4Y"

bot = Bot(token=API_TOKEN) 
dp  = Dispatcher(bot)

user_data = {}   # {user_id: dict}

@dp.message_handler(commands="start")
async def start(m: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📄 Анализ PDF", "📝 Создать договор", "❓ Задать вопрос")
    await m.answer("👋 LegalAideIPbot – помощник для ИП", reply_markup=kb)

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
        # финальный рендер
        data.update({"day": "01", "month": "января", "year": "2025",
                     "landlord_passport": "серия 1234 №567890",
                     "tenant_passport":  "серия 9876 №543210"})
        out_path = build(data, f"аренда_ИП_{uid}.docx")
        await m.reply_document(types.InputFile(out_path))
        data.clear()
    else:
        # режим поиска FAQ
        await m.answer(find_answer(m.text))

async def main():
    await dp.start_polling(bot)
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
