import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart

TOKEN = "ТВОЙ_ТОКЕН"  # вставь сюда свой токен
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

user_data = {}

# Кнопка сброса
def get_restart_keyboard():
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔄 Посчитать заново")]
    ], resize_keyboard=True)
    return kb

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привет! Я — Калькулятор расчета обоев от ДИЗ БАЛАНС 🧮\n\n"
        "Я помогу рассчитать нужное количество обоев с учётом параметров комнаты, окон и дверей.\n"
        "Все значения вводи в метрах. Если число не целое — используй точку (например: 2.5 или 0.6).",
        reply_markup=ReplyKeyboardRemove()
    )
    user_data[message.chat.id] = {}
    await message.answer("👉 Укажи длину комнаты (например: 5.0):")

@dp.message()
async def handle_input(message: Message):
    chat_id = message.chat.id
    text = message.text.strip()

    if text == "🔄 Посчитать заново":
        user_data[chat_id] = {}
        await message.answer("👉 Укажи длину комнаты (например: 5.0):", reply_markup=ReplyKeyboardRemove())
        return

    try:
        value = float(text.replace(",", "."))  # поддержка запятой
    except ValueError:
        await message.answer("Пожалуйста, введи число, например: 5")
        return

    data = user_data.get(chat_id, {})

    if "length" not in data:
        data["length"] = value
        await message.answer("👉 Укажи ширину комнаты (например: 3.0):")
    elif "width" not in data:
        data["width"] = value
        await message.answer("🧱 Укажи высоту стен (например: 2.5):")
    elif "height" not in data:
        data["height"] = value
        await message.answer("🪟 Сколько окон в комнате? (например: 1):")
    elif "windows" not in data:
        data["windows"] = int(value)
        data["window_index"] = 1
        data["window_areas"] = []
        if data["windows"] > 0:
            await message.answer(f"👉 Укажи ширину окна №1 (например: 1.2):")
        else:
            await message.answer("🚪 Сколько дверей в комнате? (например: 1):")
    elif len(data["window_areas"]) < data["windows"] * 2:
        if len(data["window_areas"]) % 2 == 0:
            data["window_areas"].append(value)
            await message.answer(f"👉 Укажи высоту окна №{data['window_index']} (например: 1.3):")
        else:
            data["window_areas"].append(value)
            data["window_index"] += 1
            if data["window_index"] <= data["windows"]:
                await message.answer(f"👉 Укажи ширину окна №{data['window_index']} (например: 1.2):")
            else:
                await message.answer("🚪 Сколько дверей в комнате? (например: 1):")
    elif "doors" not in data:
        data["doors"] = int(value)
        data["door_index"] = 1
        data["door_areas"] = []
        if data["doors"] > 0:
            await message.answer(f"👉 Укажи ширину двери №1 (например: 0.9):")
        else:
            await message.answer("📏 Укажи ширину рулона обоев (например: 0.53):")
    elif len(data["door_areas"]) < data["doors"] * 2:
        if len(data["door_areas"]) % 2 == 0:
            data["door_areas"].append(value)
            await message.answer(f"👉 Укажи высоту двери №{data['door_index']} (например: 2.0):")
        else:
            data["door_areas"].append(value)
            data["door_index"] += 1
            if data["door_index"] <= data["doors"]:
                await message.answer(f"👉 Укажи ширину двери №{data['door_index']} (например: 0.9):")
            else:
                await message.answer("📏 Укажи ширину рулона обоев (например: 0.53):")
    elif "roll_width" not in data:
        data["roll_width"] = value
        await message.answer("📏 Укажи длину рулона обоев (например: 10.05):")
    elif "roll_length" not in data:
        data["roll_length"] = value
        await message.answer("🔁 Укажи раппорт (расстояние между рисунками), например: 0.0, 0.32 или 0.64:")
    elif "rapport" not in data:
        data["rapport"] = value

        # Расчёт
        perimeter = 2 * (data["length"] + data["width"])
        wall_area = perimeter * data["height"]

        window_area = sum([data["window_areas"][i] * data["window_areas"][i+1] for i in range(0, 
len(data["window_areas"]), 2)]) if data["windows"] > 0 else 0
        door_area = sum([data["door_areas"][i] * data["door_areas"][i+1] for i in range(0, 
len(data["door_areas"]), 2)]) if data["doors"] > 0 else 0

        net_area = wall_area - window_area - door_area

        strip_height = data["height"] + data["rapport"]
        strips_per_roll = int(data["roll_length"] // strip_height)
        strips_needed = int(perimeter // data["roll_width"])
        rolls_needed = -(-strips_needed // strips_per_roll)  # округление вверх

        await message.answer(
            f"✅ Примерный результат расчёта:\n\n"
            f"🧱 Общая площадь стен: {wall_area:.2f} м²\n"
            f"🪟 Площадь окон: {window_area:.2f} м²\n"
            f"🚪 Площадь дверей: {door_area:.2f} м²\n"
            f"📐 Чистая площадь оклейки: {net_area:.2f} м²\n"
            f"📏 Требуется полос: {strips_needed}\n"
            f"📦 Рулонов нужно (с учётом раппорта): {rolls_needed}\n\n"
            f"📝 Рекомендуем взять на 1 рулон больше — на запас.",
            reply_markup=get_restart_keyboard()
        )

    user_data[chat_id] = data


# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
