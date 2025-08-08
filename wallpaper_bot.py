import os, math, asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("wallpaper-bot")

# Токен берём из переменной окружения (НЕ хардкодим)
BOT_TOKEN = os.environ["BOT_TOKEN"]

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

user_data: dict[int, dict] = {}

def kb_restart():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔄 Посчитать заново")]],
        resize_keyboard=True
    )

def pf(x: str) -> float | None:
    try:
        return float(x.strip().replace(",", "."))
    except Exception:
        return None

@dp.message(CommandStart())
async def start(m: Message):
    user_data[m.chat.id] = {}
    await m.answer(
        "Привет! Я — Калькулятор обоев 🧮\n"
        "Помогу посчитать рулоны с учётом размеров комнаты, окон и дверей.\n"
        "Все значения вводи в метрах (дробные можно с запятой или точкой).",
        reply_markup=ReplyKeyboardRemove()
    )
    await m.answer("👉 Длина комнаты (например 5.0):")

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
        def need(key, prompt, must_positive=True):
            v = pf(t)
            if v is None or (must_positive and v <= 0) or ((not must_positive) and v < 0):
                asyncio.create_task(m.answer("❌ Введи корректное число."))
                return False
            d[key] = v
            asyncio.create_task(m.answer(prompt))
            return True

        if "length" not in d and need("length", "👉 Ширина комнаты:"): return
        if "width" not in d and need("width", "🧱 Высота стен:"): return
        if "height" not in d and need("height", "🪟 Сколько окон? (можно 0):"): return

        if "windows" not in d:
            v = pf(t)
            if v is None or v < 0:
                await m.answer("❌ Введи целое число ≥ 0")
                return
            d["windows"] = int(v); d["wi"] = 1; d["w"] = []
            if d["windows"] == 0:
                await m.answer("🚪 Сколько дверей? (можно 0):")
            else:
                await m.answer("👉 Ширина окна №1:")
            return

        if len(d["w"]) < d["windows"] * 2:
            v = pf(t)
            if v is None or v < 0:
                await m.answer("❌ Введи число ≥ 0")
                return
            d["w"].append(v)
            if len(d["w"]) % 2 == 1:
                await m.answer(f"👉 Высота окна №{d['wi']}:")
            else:
                d["wi"] += 1
                if d["wi"] <= d["windows"]:
                    await m.answer("👉 Ширина следующего окна:")
                else:
                    await m.answer("🚪 Сколько дверей? (можно 0):")
            return

        if "doors" not in d:
            v = pf(t)
            if v is None or v < 0:
                await m.answer("❌ Введи целое число ≥ 0")
                return
            d["doors"] = int(v); d["di"] = 1; d["d"] = []
            if d["doors"] == 0:
                await m.answer("📏 Ширина рулона (м):")
            else:
                await m.answer("👉 Ширина двери №1:")
            return

        if len(d["d"]) < d["doors"] * 2:
            v = pf(t)
            if v is None or v < 0:
                await m.answer("❌ Введи число ≥ 0")
                return
            d["d"].append(v)
            if len(d["d"]) % 2 == 1:
                await m.answer(f"👉 Высота двери №{d['di']}:")
            else:
                d["di"] += 1
                if d["di"] <= d["doors"]:
                    await m.answer("👉 Ширина следующей двери:")
                else:
                    await m.answer("📏 Ширина рулона (м):")
            return

        if "roll_w" not in d and need("roll_w", "📏 Длина рулона (м):"): return
        if "roll_l" not in d and need("roll_l", "🔁 Раппорт (м). Если нет — 0.0:", must_positive=True): return

        if "rapport" not in d:
            v = pf(t)
            if v is None or v < 0:
                await m.answer("❌ Введи число ≥ 0")
                return
            d["rapport"] = v

            L, W, H = d["length"], d["width"], d["height"]
            per = 2 * (L + W)
            wall = per * H

            win = sum(d["w"][i] * d["w"][i+1] for i in range(0, len(d["w"]), 2)) if d["w"] else 0.0
            drs = sum(d["d"][i] * d["d"][i+1] for i in range(0, len(d["d"]), 2)) if d["d"] else 0.0
            net = max(0.0, wall - win - drs)

            rap = d["rapport"]
            drop_h = math.ceil(H / rap) * rap if rap > 0 else H

            strips_per_roll = int(d["roll_l"] // drop_h)
            if strips_per_roll <= 0:
                await m.answer("❗️Из рулона не получается ни одной полосы. Проверь параметры.",
                               reply_markup=kb_restart())
                user_data[c] = {}
                return

            strips_needed = math.ceil(per / d["roll_w"])
            rolls = math.ceil(strips_needed / strips_per_roll)

            await m.answer(
                "✅ <b>Результат</b>\n"
                f"🧱 Площадь стен: <b>{wall:.2f} м²</b>\n"
                f"🪟 Окна: <b>{win:.2f} м²</b> • 🚪 Двери: <b>{drs:.2f} м²</b>\n"
                f"📐 Чистая площадь: <b>{net:.2f} м²</b>\n\n"
                f"📏 Высота полосы: <b>{drop_h:.2f} м</b>, из рулона: <b>{strips_per_roll}</b>\n"
                f"📏 Полос нужно: <b>{strips_needed}</b>\n"
                f"📦 Рулонов: <b>{rolls}</b>\n\n"
                f"📝 Рекомендуем взять +1 рулон на запас.",
                reply_markup=kb_restart()
            )
            return

    except Exception as e:
        log.exception("flow error: %s", e)
        await m.answer("❌ Ошибка. Нажми «Посчитать заново».", reply_markup=kb_restart())

async def main():
    # снимаем вебхук и чистим старые апдейты — чтобы не было конфликта
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
