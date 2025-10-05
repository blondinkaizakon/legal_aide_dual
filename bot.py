# bot/bot.py  (aiogram 3.x, Python 3.12)
import asyncio
import tempfile
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InputFile
from core.config        import TOKEN
from core.pdf_tool      import extract_text
from core.analyzer      import analyze
from core.doc_generator import build
from core.kb_search     import find_answer

API_TOKEN = 8440749347:AAFeXggvdBjedsTHI9cOHrHvG6vUrBnka4Y
bot = Bot(token=API_TOKEN)
dp  = Dispatcher()

user_data = {}                       # {user_id: dict}

# ==================== КЛАВИАТУРА ====================
def main_menu_kb() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📄 Анализ PDF", "📝 Создать договор", "❓ Задать вопрос")
    return kb

# ==================== КОМАНДЫ ====================
@dp.message(F.command == "start")
async def cmd_start(message: types.Message):
    await message.answer("👋 LegalAideIPbot – помощник для ИП", reply_markup=main_menu_kb())

# ==================== АНАЛИЗ PDF ====================
@dp.message(F.document)
async def handle_pdf(message: types.Message):
    if not message.document.file_name.lower().endswith(".pdf"):
        return await message.reply("Пришлите PDF-договор")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        await message.bot.download(message.document.file_id, tmp.name)
        text = extract_text(tmp.name)
        os.unlink(tmp.name)
        risks = "\n".join(analyze(text))
        await message.answer(risks or "✅ Критических рисков не обнаружено")

# ==================== ГЕНЕРАТОР ДОГОВОРА ====================
@dp.message(F.text == "📝 Создать договор")
async def new_contract(message: types.Message):
    user_data[message.from_user.id] = {}
    await message.answer("Введите город (например, Москва):")

# ==================== FAQ ====================
@dp.message(F.text == "❓ Задать вопрос")
async def ask_question(message: types.Message):
    await message.answer("Напишите ваш вопрос:")

# ==================== СБОР ДАННЫХ + ГЕНЕРАЦИЯ ====================
@dp.message()
async def collect_data(message: types.Message):
    uid  = message.from_user.id
    data = user_data.setdefault(uid, {})

    if "city" not in data:
        data["city"] = message.text
        return await message.answer("Арендодатель (ФИО полностью):")
    if "landlord" not in data:
        data["landlord"] = message.text
        return await message.answer("Арендатор (ФИО полностью):")
    if "tenant" not in data:
        data["tenant"] = message.text
        return await message.answer("Описание помещения (адрес, площадь):")
    if "property" not in data:
        data["property"] = message.text
        return await message.answer("Сумма аренды в месяц (руб.):")
    if "rent" not in data:
        data["rent"] = message.text
        data.update({"day": "01", "month": "января", "year": "2025",
                     "landlord_passport": "серия 1234 №567890",
                     "tenant_passport":  "серия 9876 №543210"})
        out_path = build(data, f"аренда_ИП_{uid}.docx")
        await message.reply_document(InputFile(out_path))
        data.clear()                       # сброс после отправки
    else:
        # FAQ-режим
        await message.answer(find_answer(message.text))

# ==================== ЗАПУСК ====================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
