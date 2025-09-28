import asyncio
import aiosqlite
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, SuccessfulPaymentFilter
from aiogram.types import (
    LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, PreCheckoutQuery
)

# ---------- Настройки ----------
TOKEN = "7615768301:AAGxhDTqCzI8-4lu0oo2v0cOFKS2_x1T-8o"
ADMIN_ID = 6486579332
PAYMENT_PROVIDER_TOKEN = ""   # пусто для Stars
CURRENCY = "XTR"              # Telegram Stars
# --------------------------------

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- База данных ---
async def init_db():
    async with aiosqlite.connect("students.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS students (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language_code TEXT,
            is_premium INTEGER
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            date TEXT,
            type TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            currency TEXT,
            date TEXT,
            payload TEXT
        )
        """)
        await db.commit()

# --- Быстрое меню ---
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🆘 Помощь")],
        [KeyboardButton(text="💎 Поддержать проект")],
        [KeyboardButton(text="✉️ Сообщение админу")]
    ],
    resize_keyboard=True
)

# --- START ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для связи с админом.\n"
        "Выберите действие через меню или используйте команды:\n\n"
        "/help — помощь\n"
        "/privacy — политика конфиденциальности\n"
        "/myid — ваш ID\n"
        "/donate — поддержать проект\n"
        "/letter текст — написать админу",
        reply_markup=main_menu
    )

# --- HELP ---
@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        "🆘 Помощь\n\n"
        "Доступные команды:\n"
        "/start — главное меню\n"
        "/help — эта справка\n"
        "/privacy — политика конфиденциальности\n"
        "/myid — показать ваш Telegram ID\n"
        "/donate — поддержать проект звёздами\n"
        "/letter текст — написать админу"
    )

# --- PRIVACY ---
@dp.message(Command("privacy"))
async def privacy(message: types.Message):
    await message.answer(
        "🔐 Политика конфиденциальности:\n\n"
        "1) Сохраняем только ваш Telegram ID, имя и сообщения для связи с администратором.\n"
        "2) Данные не передаются третьим лицам.\n"
        "3) Хотите удалить свои данные — напишите админу.\n\n"
        "Спасибо за доверие!"
    )

# --- MYID ---
@dp.message(Command("myid"))
async def myid(message: types.Message):
    user = message.from_user
    await message.answer(
        f"🆔 Ваш Telegram ID: `{user.id}`\n"
        f"👤 Username: @{user.username or 'нет'}",
        parse_mode="Markdown"
    )

# --- DONATE ---
@dp.message(Command("donate"))
async def donate_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ 1 Star", callback_data="donate_1")],
            [InlineKeyboardButton(text="⭐ 5 Stars", callback_data="donate_5")],
            [InlineKeyboardButton(text="⭐ 10 Stars", callback_data="donate_10")]
        ]
    )
    await message.answer("Выберите сумму поддержки:", reply_markup=kb)

@dp.callback_query(F.data.startswith("donate_"))
async def donate_callback(callback: types.CallbackQuery):
    stars = int(callback.data.split("_")[1])
    user = callback.from_user

    prices = [LabeledPrice(label=f"Поддержка — {stars} Stars", amount=stars)]

    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=f"Поддержка — {stars} Stars",
        description="Спасибо за поддержку проекта!",
        payload=f"donate_{user.id}_{int(datetime.utcnow().timestamp())}",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency=CURRENCY,
        prices=prices
    )
    await callback.answer()

# --- Pre-checkout ---
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_q: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

# --- Успешная оплата ---
@dp.message(SuccessfulPaymentFilter())
async def got_payment(message: types.Message):
    pay = message.successful_payment
    user = message.from_user

    async with aiosqlite.connect("students.db") as db:
        await db.execute(
            "INSERT INTO donations (user_id, amount, currency, date, payload) VALUES (?, ?, ?, ?, ?)",
            (user.id, pay.total_amount, pay.currency, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pay.invoice_payload)
        )
        await db.commit()

    await message.answer("✅ Спасибо за поддержку! ❤️")
    await bot.send_message(
        ADMIN_ID,
        f"💰 Донат от @{user.username or 'Без ника'} ({user.id})\n"
        f"Сумма: {pay.total_amount} {pay.currency}\n"
        f"Payload: {pay.invoice_payload}"
    )

# --- LETTER ---
@dp.message(Command("letter"))
async def letter(message: types.Message):
    text = message.text.replace("/letter", "").strip()
    if not text:
        return await message.answer("❌ Напиши так: /letter текст")

    user = message.from_user
    async with aiosqlite.connect("students.db") as db:
        await db.execute("INSERT INTO messages (user_id, message, date, type) VALUES (?, ?, ?, ?)",
                         (user.id, text, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "letter"))
        await db.commit()

    await message.answer("✅ Письмо отправлено админу!")
    await bot.send_message(ADMIN_ID, f"📨 Письмо от @{user.username or 'Без ника'} ({user.id}):\n{text}")

# --- REPLY ---
@dp.message(Command("reply"))
async def reply(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.answer("Используй: /reply user_id текст")

    user_id, text = int(args[1]), args[2]
    try:
        await bot.send_message(user_id, f"📩 Ответ от администратора:\n\n{text}")
        await message.answer("✅ Ответ отправлен")
    except:
        await message.answer("⚠ Не удалось отправить сообщение")

# --- Обработка кнопок меню ---
@dp.message(F.text == "🆘 Помощь")
async def menu_help(message: types.Message):
    await help_cmd(message)

@dp.message(F.text == "💎 Поддержать проект")
async def menu_donate(message: types.Message):
    await donate_cmd(message)

@dp.message(F.text == "✉️ Сообщение админу")
async def menu_letter(message: types.Message):
    await message.answer("Напиши своё сообщение, и я отправлю его админу.\n\n"
                         "Или используй /letter текст")

# --- Все остальные тексты ---
@dp.message(F.text)
async def forward_msg(message: types.Message):
    if message.text.startswith("/"):
        return

    user = message.from_user
    async with aiosqlite.connect("students.db") as db:
        await db.execute("""
        INSERT OR REPLACE INTO students (user_id, username, first_name, last_name, language_code, is_premium)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user.id,
            user.username,
            user.first_name,
            user.last_name,
            user.language_code,
            1 if getattr(user, "is_premium", False) else 0
        ))
        await db.execute("INSERT INTO messages (user_id, message, date, type) VALUES (?, ?, ?, ?)",
                         (user.id, message.text, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "message"))
        await db.commit()

    await bot.send_message(
        ADMIN_ID,
        f"📩 Сообщение от @{user.username or 'Без ника'} ({user.id}):\n{message.text}"
    )

# --- Запуск ---
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
