import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)

# --- токен из переменных окружения ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("❌ Нет BOT_TOKEN. Задай его в Render → Environment.")

# --- логирование ---
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("wallpaper-bot")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- память по пользователям ---
user_data: dict[int, dict] = {}

def kb_restart() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔄 Посчитать заново")]],
        resize_keyboard=True
    )

def pf(text: str) -> float | None:
    """float с поддержкой запятой и тримом пробелов"""
    if not text:
        return None
    try:
        return float(text.strip().replace(",", "."))
    except Exception:
        return None

@dp.message(CommandStart())
async def start(message: Message):
    user_data[message.chat.id] = {}
    await message.answer(
        "Привет! Я — Калькулятор обоев 🧮\n\n"
        "Помогу посчитать рулоны с учётом размеров комнаты, окон и дверей.\n"
        "Вводи значения в метрах, дробные можно с запятой или точкой.",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer("👉 Длина комнаты (например 5.0):")

@dp.message()
async def flow(m: Message):
    c = m.chat.id
    t = (m.text or "").strip()

    if t == "🔄 Посчитать заново":
        user_data[c] = {}
        await m.answer("👉 Длина комнаты:")
        return

    d = user_data.setdefault(c, {})

    try:
        # Шаги по порядку
        if "length" not in d:
            v = pf(t)
            if v is None or v <= 0:
                await m.answer("❌ Введи корректную длину, например 5.0")
                return
            d["length"] = v
            await m.answer("👉 Ширина комнаты (например 3.0):")
            return

        if "width" not in d:
            v = pf(t)
            if v is None or v <= 0:
                await m.answer("❌ Введи корректную ширину, например 3.0")
                return
            d["width"] = v
            await m.answer("👉 Высота стен (например 2.6):")
            return

        if "height" not in d:
            v = pf(t)
            if v is None or v <= 0:
                await m.answer("❌ Введи корректную высоту, например 2.6")
                return
            d["height"] = v
            await m.answer("🪟 Сколько окон? (целое число, например 1 или 0):")
            return

        if "windows" not in d:
            iv = pf(t)
            if iv is None or iv < 0 or int(iv) != iv:
                await m.answer("❌ Введи целое число окон, например 1 или 0")
                return
            d["windows"] = int(iv)
            d["window_areas"] = []
            d["w_idx"] = 1
            if d["windows"] == 0:
                await m.answer("🚪 Сколько дверей? (целое число):")
            else:
                await m.answer(f"👉 Ширина окна №{d['w_idx']} (м):")
            return

        # Сбор размеров окон (парами: ширина, высота)
        if len(d["window_areas"]) < d["windows"] * 2:
            v = pf(t)
            if v is None or v <= 0:
                await m.answer("❌ Введи положительное число (м)")
                return
            d["window_areas"].append(v)
            # если только что ввели ширину — спросим высоту
            if len(d["window_areas"]) % 2 == 1:
                await m.answer(f"👉 Высота окна №{d['w_idx']} (м):")
            else:
                d["w_idx"] += 1
                if d["w_idx"] <= d["windows"]:
                    await m.answer(f"👉 Ширина окна №{d['w_idx']} (м):")
                else:
                    await m.answer("🚪 Сколько дверей? (целое число):")
            return

        if "doors" not in d:
            iv = pf(t)
            if iv is None or iv < 0 or int(iv) != iv:
                await m.answer("❌ Введи целое число дверей, например 1 или 0")
                return
            d["doors"] = int(iv)
            d["door_areas"] = []
            d["d_idx"] = 1
            if d["doors"] == 0:
                await m.answer("📏 Ширина рулона (например 0.53):")
            else:
                await m.answer(f"👉 Ширина двери №{d['d_idx']} (м):")
            return

        # Сбор размеров дверей
        if len(d["door_areas"]) < d["doors"] * 2:
            v = pf(t)
            if v is None or v <= 0:
                await m.answer("❌ Введи положительное число (м)")
                return
            d["door_areas"].append(v)
            if len(d["door_areas"]) % 2 == 1:
                await m.answer(f"👉 Высота двери №{d['d_idx']} (м):")
            else:
                d["d_idx"] += 1
                if d["d_idx"] <= d["doors"]:
                    await m.answer(f"👉 Ширина двери №{d['d_idx']} (м):")
                else:
                    await m.answer("📏 Ширина рулона (например 0.53):")
            return

        if "roll_width" not in d:
            v = pf(t)
            if v is None or v <= 0:
                await m.answer("❌ Ширина рулона в метрах, например 0.53")
                return
            d["roll_width"] = v
            await m.answer("📏 Длина рулона (например 10.05):")
            return

        if "roll_length" not in d:
            v = pf(t)
            if v is None or v <= 0:
                await m.answer("❌ Длина рулона в метрах, например 10.05")
                return
            d["roll_length"] = v
            await m.answer("🔁 Раппорт (0, 0.32, 0.64 и т.п.):")
            return

        if "rapport" not in d:
            v = pf(t)
            if v is None or v < 0:
                await m.answer("❌ Раппорт не должен быть отрицательным")
                return
            d["rapport"] = v

            # ---- расчет ----
            perimeter = 2 * (d["length"] + d["width"])
            wall_area = perimeter * d["height"]

            window_area = sum(
                d["window_areas"][i] * d["window_areas"][i + 1]
                for i in range(0, len(d["window_areas"]), 2)
            )
            door_area = sum(
                d["door_areas"][i] * d["door_areas"][i + 1]
                for i in range(0, len(d["door_areas"]), 2)
            )

            net_area = wall_area - window_area - door_area

            strip_height = d["height"] + d["rapport"]
            if strip_height <= 0 or d["roll_width"] <= 0:
                await m.answer("❌ Некорректные параметры для расчёта.")
                user_data[c] = {}
                return

            strips_per_roll = int(d["roll_length"] // strip_height)  # целых полос из рулона
            strips_needed = int(perimeter // d["roll_width"])        # сколько полос на периметр

            if strips_per_roll == 0:
                await m.answer("❌ Слишком большой раппорт/высота — из рулона не выходит ни одной целой полосы.")
                user_data[c] = {}
                return

            rolls_needed = (strips_needed + strips_per_roll - 1) // strips_per_roll  # округление вверх

            await m.answer(
                "✅ Результаты:\n\n"
                f"• Площадь стен: <b>{wall_area:.2f} м²</b>\n"
                f"• Площадь окон: <b>{window_area:.2f} м²</b>\n"
                f"• Площадь дверей: <b>{door_area:.2f} м²</b>\n"
                f"• Чистая площадь оклейки: <b>{net_area:.2f} м²</b>\n"
                f"• Полос нужно: <b>{strips_needed}</b>\n"
                f"• Рулонов (с раппортом): <b>{rolls_needed}</b>\n\n"
                f"Совет: возьми на 1 рулон больше — на запас.",
                reply_markup=kb_restart(),
                parse_mode="HTML"
            )

            # сбросим состояние, чтобы новая сессия начиналась с длины
            user_data[c] = {}
            return

        # если что-то вне сценария
        await m.answer("❌ Ошибка. Нажми «🔄 Посчитать заново».", reply_markup=kb_restart())

    except Exception as e:
        log.exception("flow error: %s", e)
        await m.answer("❌ Неожиданная ошибка. Нажми «🔄 Посчитать заново».", reply_markup=kb_restart())
        user_data[c] = {}

# --- запуск ---
async def main():
    # На всякий сбрасываем вебхук, если он вдруг стоял
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
