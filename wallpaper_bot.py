import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart

# Получаем токен из переменной окружения Render
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set! Please set it in Render Environment Variables.")

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Храним данные пользователей
user_data = {}

# Кнопка "Посчитать заново"
main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🔄 Посчитать заново")]],
    resize_keyboard=True
)

# Парсинг числа с поддержкой запятой и точки
def parse_float(value):
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привет! Я — Калькулятор расчета обоев 🪄\n"
        "Все значения вводи в метрах (дробные можно с запятой или точкой).",
        reply_markup=main_kb
    )
    user_data[message.chat.id] = {}
    await message.answer("👉 Длина комнаты (например 5.0):")

@dp.message()
async def flow(message: Message):
    chat_id = message.chat.id
    text = (message.text or "").strip()

    # Начать заново
    if text == "🔄 Посчитать заново":
        user_data[chat_id] = {}
        await message.answer("👉 Длина комнаты (например 5.0):")
        return

    d = user_data.setdefault(chat_id, {})

    def need(key, prompt, must_positive=True):
        value = parse_float(text)
        if value is None or (must_positive and value <= 0):
            asyncio.create_task(message.answer("❌ Введи корректное число, например 5.0"))
            return False
        d[key] = value
        asyncio.create_task(message.answer(prompt))
        return True

    # Пошаговый опрос
    if "length" not in d:
        if not need("length", "👉 Ширина комнаты (например 3.0):"):
            return
    elif "width" not in d:
        if not need("width", "👉 Высота стен (например 2.7):"):
            return
    elif "height" not in d:
        if not need("height", "📏 Сколько окон в комнате?:", must_positive=False):
            return
    elif "windows" not in d:
        value = parse_float(text)
        if value is None or value < 0:
            await message.answer("❌ Введи корректное число, например 2")
            return
        d["windows"] = int(value)
        await message.answer("📏 Сколько дверей в комнате?:")
    elif "doors" not in d:
        value = parse_float(text)
        if value is None or value < 0:
            await message.answer("❌ Введи корректное число, например 1")
            return
        d["doors"] = int(value)
        await message.answer("📐 Длина рулона обоев (например 10.0):")
    elif "roll_length" not in d:
        if not need("roll_length", "📐 Ширина рулона обоев (например 0.53):"):
            return
    elif "roll_width" not in d:
        if not need("roll_width", "🔄 Укажи раппорт (например 0, 0.32 или 0.64 — если нет, то 0):", 
must_positive=False):
            return
    elif "rapport" not in d:
        if not need("rapport", "✅ Считаю..."):
            return

        # --- Расчёт ---
        length = d["length"]
        width = d["width"]
        height = d["height"]
        windows = d["windows"]
        doors = d["doors"]
        roll_length = d["roll_length"]
        roll_width = d["roll_width"]
        rapport = d["rapport"]

        # Площадь комнаты
        perimeter = 2 * (length + width)
        wall_area = perimeter * height

        # Вычитаем окна и двери
        wall_area -= windows * (1.5 * 1.2)
        wall_area -= doors * (2.0 * 0.8)

        # Кол-во полос из рулона
        if rapport > 0:
            effective_height = height + (rapport - height % rapport if height % rapport != 0 else 0)
        else:
            effective_height = height

        strips_per_roll = int(roll_length // effective_height)
        strip_width_area = roll_width * effective_height
        total_strips_needed = wall_area / (roll_width * effective_height)
        rolls_needed = int((total_strips_needed / strips_per_roll) + 0.9999)

        await message.answer(
            f"📊 Для вашей комнаты нужно примерно: <b>{rolls_needed}</b> рулонов обоев.\n"
            f"📝 Рекомендую взять с запасом 1 рулон.",
            reply_markup=main_kb
        )

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
