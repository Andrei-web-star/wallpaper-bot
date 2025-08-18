# wallpaper_bot.py
import os
import math
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

# ===== Настройки =====
TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not TOKEN:
    raise RuntimeError("BOT_TOKEN не задан. Добавь переменную окружения BOT_TOKEN в Render.")

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# ===== Клавиатуры =====
def kb_restart() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔄 Посчитать заново")]],
        resize_keyboard=True
    )

# ===== Состояния =====
class S(StatesGroup):
    length = State()
    width = State()
    height = State()
    windows = State()
    window_dim = State()
    doors = State()
    door_dim = State()
    roll_width = State()
    roll_length = State()
    rapport = State()

# ===== Утилиты =====
def pfloat(t: str) -> float | None:
    try:
        return float((t or "").replace(",", "."))
    except Exception:
        return None

def pint_nonneg(t: str) -> int | None:
    try:
        v = int(str(t).strip())
        return v if v >= 0 else None
    except Exception:
        return None

async def ask(m: Message, text: str, remove_kb: bool = False):
    await m.answer(text, reply_markup=(ReplyKeyboardRemove() if remove_kb else None))

# ===== Старт =====
@dp.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    await ask(m,
        "Привет! Я — <b>Калькулятор обоев от ДИЗ БАЛАНС</b> 🧮\n\n"
        "Помогу посчитать рулоны с учётом размеров комнаты, окон и дверей.\n"
        "Все значения вводи <b>в метрах</b> (дробные можно с запятой или точкой).",
        remove_kb=True
    )
    await ask(m, "👉 Укажи <b>длину</b> комнаты (например: <code>5</code>):")
    await state.set_state(S.length)

@dp.message(F.text == "🔄 Посчитать заново")
async def restart(m: Message, state: FSMContext):
    await start(m, state)

# ===== Сбор параметров =====
@dp.message(S.length)
async def get_length(m: Message, state: FSMContext):
    v = pfloat(m.text)
    if not v or v <= 0:
        return await ask(m, "❌ Введи положительное число. Пример: <code>5</code>")
    await state.update_data(length=v)
    await ask(m, "👉 Укажи <b>ширину</b> комнаты (например: <code>3</code>):")
    await state.set_state(S.width)

@dp.message(S.width)
async def get_width(m: Message, state: FSMContext):
    v = pfloat(m.text)
    if not v or v <= 0:
        return await ask(m, "❌ Введи положительное число. Пример: <code>3</code>")
    await state.update_data(width=v)
    await ask(m, "👉 Укажи <b>высоту стен</b> (например: <code>2.7</code>):")
    await state.set_state(S.height)

@dp.message(S.height)
async def get_height(m: Message, state: FSMContext):
    v = pfloat(m.text)
    if not v or v <= 0:
        return await ask(m, "❌ Введи положительное число. Пример: <code>2.7</code>")
    await state.update_data(height=v)
    await ask(m, "🪟 Сколько <b>окон</b> в комнате? (например: <code>1</code>, можно <code>0</code>):")
    await state.set_state(S.windows)

@dp.message(S.windows)
async def get_windows(m: Message, state: FSMContext):
    n = pint_nonneg(m.text)
    if n is None:
        return await ask(m, "❌ Введи целое число ≥ 0. Пример: <code>1</code>")
    await state.update_data(windows=n, window_idx=1, window_dims=[])
    if n == 0:
        await ask(m, "🚪 Сколько <b>дверей</b> в комнате? (например: <code>1</code>, можно <code>0</code>):")
        return await state.set_state(S.doors)
    await ask(m, f"👉 Укажи <b>ширину</b> окна №{1} (м), например: <code>1.2</code>")
    await state.set_state(S.window_dim)

@dp.message(S.window_dim)
async def get_window_dim(m: Message, state: FSMContext):
    data = await state.get_data()
    idx = int(data["window_idx"])
    dims: list[float] = list(data["window_dims"])
    v = pfloat(m.text)
    if not v or v <= 0:
        return await ask(m, "❌ Введи положительное число, например: <code>1.2</code>")

    # если только ширина — ждём высоту
    if len(dims) % 2 == 0:
        dims.append(v)
        await state.update_data(window_dims=dims)
        return await ask(m, f"👉 Укажи <b>высоту</b> окна №{idx} (м), например: <code>1.3</code>")
    else:
        # была ширина, пришла высота -> окно завершено
        dims.append(v)
        idx += 1
        await state.update_data(window_dims=dims, window_idx=idx)
        if idx <= data["windows"]:
            await ask(m, f"👉 Укажи <b>ширину</b> окна №{idx} (м), например: <code>1.2</code>")
        else:
            await ask(m, "🚪 Сколько <b>дверей</b> в комнате? (например: <code>1</code>, можно <code>0</code>):")
            await state.set_state(S.doors)

@dp.message(S.doors)
async def get_doors(m: Message, state: FSMContext):
    n = pint_nonneg(m.text)
    if n is None:
        return await ask(m, "❌ Введи целое число ≥ 0. Пример: <code>1</code>")
    await state.update_data(doors=n, door_idx=1, door_dims=[])
    if n == 0:
        await ask(m, "📏 Укажи <b>ширину рулона</b> обоев (м), например: <code>0.53</code>:")
        return await state.set_state(S.roll_width)
    await ask(m, f"👉 Укажи <b>ширину</b> двери №{1} (м), например: <code>0.9</code>")
    await state.set_state(S.door_dim)

@dp.message(S.door_dim)
async def get_door_dim(m: Message, state: FSMContext):
    data = await state.get_data()
    idx = int(data["door_idx"])
    dims: list[float] = list(data["door_dims"])
    v = pfloat(m.text)
    if not v or v <= 0:
        return await ask(m, "❌ Введи положительное число, например: <code>0.9</code>")

    if len(dims) % 2 == 0:
        dims.append(v)
        await state.update_data(door_dims=dims)
        return await ask(m, f"👉 Укажи <b>высоту</b> двери №{idx} (м), например: <code>2.0</code>")
    else:
        dims.append(v)
        idx += 1
        await state.update_data(door_dims=dims, door_idx=idx)
        if idx <= data["doors"]:
            await ask(m, f"👉 Укажи <b>ширину</b> двери №{idx} (м), например: <code>0.9</code>")
        else:
            await ask(m, "📏 Укажи <b>ширину рулона</b> обоев (м), например: <code>0.53</code>:")
            await state.set_state(S.roll_width)

@dp.message(S.roll_width)
async def get_roll_w(m: Message, state: FSMContext):
    v = pfloat(m.text)
    if not v or v <= 0:
        return await ask(m, "❌ Введи положительное число. Пример: <code>0.53</code>")
    await state.update_data(roll_width=v)
    await ask(m, "📏 Укажи <b>длину рулона</b> (м), например: <code>10.05</code>:")
    await state.set_state(S.roll_length)

@dp.message(S.roll_length)
async def get_roll_l(m: Message, state: FSMContext):
    v = pfloat(m.text)
    if not v or v <= 0:
        return await ask(m, "❌ Введи положительное число. Пример: <code>10.05</code>")
    await state.update_data(roll_length=v)
    await ask(m, "🔁 Укажи <b>раппорт</b> (м). Если нет — введи <code>0</code>. Примеры: <code>0</code>, <code>0.32</code>, <code>0.64</code>:")
    await state.set_state(S.rapport)

# ===== Финальный расчёт =====
@dp.message(S.rapport)
async def calc(m: Message, state: FSMContext):
    v = pfloat(m.text)
    if v is None or v < 0:
        return await ask(m, "❌ Раппорт должен быть числом ≥ 0. Пример: <code>0.32</code>")
    d = await state.update_data(rapport=v)
    try:
        L = d["length"]
        W = d["width"]
        H = d["height"]
        perim = 2 * (L + W)
        wall_area = perim * H

        def sum_pairs(arr: list[float]) -> float:
            return sum(arr[i] * arr[i + 1] for i in range(0, len(arr), 2))

        window_area = sum_pairs(d.get("window_dims", []))
        door_area = sum_pairs(d.get("door_dims", []))
        net_area = max(wall_area - window_area - door_area, 0.0)

        roll_w = d["roll_width"]
        roll_l = d["roll_length"]
        rapport = d["rapport"]

        # высота полосы с учётом раппорта (округляем вверх до кратной раппорту величины)
        if rapport and rapport > 0:
            strips_height = math.ceil(H / rapport) * rapport
        else:
            strips_height = H

        if strips_height <= 0 or roll_l < strips_height:
            return await m.answer(
                "❌ Невозможно нарезать ни одной полосы из рулона.\n"
                "Проверь значения: высота, длина рулона и раппорт.",reply_markup=kb_restart()
            )

        strips_per_roll = int(roll_l // strips_height)
        strips_needed = math.ceil(perim / roll_w)
        rolls_needed = math.ceil(strips_needed / strips_per_roll)

        await m.answer(
            "✅ <b>Результаты расчёта</b>\n\n"
            f"🧱 Общая площадь стен: <b>{wall_area:.2f} м²</b>\n"
            f"🪟 Площадь окон: <b>{window_area:.2f} м²</b>\n"
            f"🚪 Площадь дверей: <b>{door_area:.2f} м²</b>\n"
            f"📐 Чистая площадь оклейки: <b>{net_area:.2f} м²</b>\n\n"
            f"📏 Высота полосы (с учётом раппорта): <b>{strips_height:.2f} м</b>\n"
            f"🧻 Полос из рулона: <b>{strips_per_roll}</b>\n"
            f"📑 Требуется полос: <b>{strips_needed}</b>\n"
            f"📦 Рулонов нужно: <b>{rolls_needed}</b>\n\n"
            f"ℹ️ Лучше взять на <b>1 рулон больше</b> — на запас.",
            reply_markup=kb_restart()
        )
    except Exception as e:
        await m.answer("❌ Неожиданная ошибка. Нажми «🔄 Посчитать заново».", reply_markup=kb_restart())
    finally:
        await state.clear()

# ===== Запуск (Render/локально) =====
async def main():
    # На всякий: если где-то был вебхук — отключим
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
