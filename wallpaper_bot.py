import os
import math
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

# === Настройки ===
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment variables.")

# Логирование (полезно на Render)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("wallpaper-bot")

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# === Память сессий (простая in‑memory) ===
user_data: dict[int, dict] = {}

# === Кнопка «сброс» ===
def restart_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔄 Посчитать заново")]],
        resize_keyboard=True
    )

# --- утилиты ---
def pf(s: str | None) -> float | None:
    """parse float с поддержкой запятой и тримом пробелов"""
    if not s:
        return None
    try:
        return float(s.strip().replace(",", "."))
    except ValueError:
        return None

def need_positive(m: Message, d: dict, key: str, value: float | None, prompt: str) -> bool:
    """Проверить, что value валидно и положительно. Если ок — записать и спросить следующее."""
    if value is None or value <= 0:
        asyncio.create_task(m.answer("❌ Введи корректное положительное число."))
        return False
    d[key] = value
    asyncio.create_task(m.answer(prompt))
    return True


# === Старт ===
@dp.message(CommandStart())
async def start(message: Message):
    user_data[message.chat.id] = {}
    await message.answer(
        "Привет! Я — <b>Калькулятор обоев</b> 🧮\n\n"
        "Помогу посчитать рулоны с учётом размеров комнаты, окон и дверей.\n"
        "Все значения вводи <b>в метрах</b> (дробные можно с запятой или точкой).\n\n"
        "👉 Укажи <b>длину</b> комнаты (например: <code>5</code>):",
        reply_markup=ReplyKeyboardRemove()
    )


# === Основной поток ввода ===
@dp.message()
async def flow(m: Message):
    c = m.chat.id
    t = (m.text or "").strip()

    # Сброс
    if t == "🔄 Посчитать заново":
        user_data[c] = {}
        await m.answer("👉 Укажи <b>длину</b> комнаты (например: <code>5</code>):",
                       reply_markup=ReplyKeyboardRemove())
        return

    d = user_data.setdefault(c, {})

    try:
        # 1) Длина
        if "length" not in d:
            v = pf(t)
            if not need_positive(m, d, "length", v, "👉 Укажи <b>ширину</b> комнаты (например: <code>3</code>):"):
                return
            return

        # 2) Ширина (спрашиваем ОДИН раз)
        if "width" not in d:
            v = pf(t)
            if not need_positive(m, d, "width", v, "👉 Укажи <b>высоту стен</b> (например: <code>2.7</code>):"):
                return
            return

        # 3) Высота
        if "height" not in d:
            v = pf(t)
            if not need_positive(m, d, "height", v, "🪟 Сколько <b>окон</b> в комнате? (например: <code>1</code>):"):
                return
            return

        # 4) Кол-во окон
        if "windows" not in d:
            try:
                count = int(float(t.replace(",", ".")))
                if count < 0:
                    raise ValueError
            except ValueError:
                await m.answer("❌ Введи целое неотрицательное число (например: 0, 1, 2).")
                return
            d["windows"] = count
            d["w_idx"] = 1
            d["w_dims"] = []  # [w1, h1, w2, h2, ...]
            if count == 0:
                await m.answer("🚪 Сколько <b>дверей</b>? (например: <code>1</code>):")
            else:
                await m.answer("👉 Укажи <b>ширину окна №1</b> (м), например: <code>1.2</code>")
            return

        # 5) Размеры окон (по два значения на окно)
        if len(d["w_dims"]) < d["windows"] * 2:
            v = pf(t)
            if v is None or v <= 0:
                await m.answer("❌ Введи положительное число в метрах.")
                return
            d["w_dims"].append(v)
            # если ввели ширину — спросить высоту; если ввели высоту — перейти к следующему окну/к дверям
            if len(d["w_dims"]) % 2 == 1:
                await m.answer(f"👉 Укажи <b>высоту окна №{d['w_idx']}</b> (м):")
            else:
                d["w_idx"] += 1
                if d["w_idx"] <= d["windows"]:
                    await m.answer(f"👉 Укажи <b>ширину окна №{d['w_idx']}</b> (м):")
                else:
                    await m.answer("🚪 Сколько <b>дверей</b>? (например: <code>1</code>):")
            return

        # 6) Кол-во дверей
        if "doors" not in d:
            try:
                count = int(float(t.replace(",", ".")))
                if count < 0:
                    raise ValueError
            except ValueError:
                await m.answer("❌ Введи целое неотрицательное число (например: 0, 1).")
                return
            d["doors"] = count
            d["d_idx"] = 1
            d["d_dims"] = []
            if count == 0:
                await m.answer("📏 Укажи <b>ширину рулона</b> (м), например: <code>0.53</code>")
            else:
                await m.answer("👉 Укажи <b>ширину двери №1</b> (м):")
            return

        # 7) Размеры дверей
        if len(d["d_dims"]) < d["doors"] * 2:
            v = pf(t)
            if v is None or v <= 0:
                await m.answer("❌ Введи положительное число в метрах.")
                return
            d["d_dims"].append(v)
            if len(d["d_dims"]) % 2 == 1:
                await m.answer(f"👉 Укажи <b>высоту двери №{d['d_idx']}</b> (м):")
            else:
                d["d_idx"] += 1
                if d["d_idx"] <= d["doors"]:
                    await m.answer(f"👉 Укажи <b>ширину двери №{d['d_idx']}</b> (м):")
                else:
                    await m.answer("📏 Укажи <b>ширину рулона</b> (м), например: <code>0.53</code>")
            return

        # 8) Ширина рулона
        if "roll_w" not in d:
            v = pf(t)
            if not need_positive(m, d, "roll_w", v, "📏 Укажи <b>длину рулона</b> (м), например: 
<code>10.05</code>"):
                return
            return

        # 9) Длина рулона
        if "roll_l" not in d:
            v = pf(t)
            if not need_positive(m, d, "roll_l", v, "🔁 Укажи <b>раппорт</b> (м). Если нет — <code>0</code>:"):
                return
            return

        # 10) Раппорт
        if "rapport" not in d:
            v = pf(t)
            if v is None or v < 0:
                await m.answer("❌ Раппорт не может быть отрицательным. Введи число ≥ 0.")
                return
            d["rapport"] = v

            # === Расчёт ===
            perim = 2 * (d["length"] + d["width"])
            wall_area = perim * d["height"]

            w_area = sum(d["w_dims"][i] * d["w_dims"][i + 1] for i in range(0, len(d["w_dims"]), 2))
            d_area = sum(d["d_dims"][i] * d["d_dims"][i + 1] for i in range(0, len(d["d_dims"]), 2))
            net_area = max(wall_area - w_area - d_area, 0.0)

            # учёт раппорта (упрощённо: добавляем раппорт к высоте отреза)
            strip_height = d["height"] + (d["rapport"] if d["rapport"] > 0 else 0)
            if strip_height <= 0 or d["roll_l"] <= 0 or d["roll_w"] <= 0:
                await m.answer("❌ Неверные параметры рулона/высоты.")
                return

            strips_per_roll = int(d["roll_l"] // strip_height)
            if strips_per_roll < 1:
                await m.answer("❌ Из одного рулона не получается ни одной полосы при заданном раппорте.")
                return

            strips_needed = math.ceil(perim / d["roll_w"])
            rolls_needed = math.ceil(strips_needed / strips_per_roll)

            await m.answer(
                "<b>✅ Результат расчёта:</b>\n\n"
                f"🧱 Площадь стен: <b>{wall_area:.2f} м²</b>\n"
                f"🪟 Площадь окон: <b>{w_area:.2f} м²</b>\n"
                f"🚪 Площадь дверей: <b>{d_area:.2f} м²</b>\n"
                f"📐 Чистая площадь оклейки: <b>{net_area:.2f} м²</b>\n\n"
                f"📏 Полос на периметр: <b>{strips_needed}</b>\n"
                f"🎯 Полос из 1 рулона: <b>{strips_per_roll}</b>\n"
                f"📦 Нужно рулонов: <b>{rolls_needed}</b>\n\n"
                "📝 Рекомендуем взять +1 рулон <i>на запас</i>.",
                reply_markup=restart_kb()
            )
            return

        # если сюда попали — ждём новое вычисление
        await m.answer("Нажми «🔄 Посчитать заново», чтобы начать новый расчёт.", reply_markup=restart_kb())

    except Exception as e:
        log.exception("wallpaper flow error: %s", e)
        await m.answer("❌ Неожиданная ошибка. Нажми «🔄 Посчитать заново».", reply_markup=restart_kb())
        user_data[c] = {}


# === Запуск ===
async def main():
    # на всякий на Render можно сбросить старый вебхук
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
