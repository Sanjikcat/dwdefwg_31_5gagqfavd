import asyncio
import sqlite3
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, LabeledPrice, PreCheckoutQuery

# 🔹 Логирование (будет видно в Railway logs)
logging.basicConfig(level=logging.INFO)

# 🔹 Токен берем из переменной окружения (Railway → Variables)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Установи его в Railway → Variables.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 🔹 Подключение к SQLite
DB_PATH = "students.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        group_name TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# 🔹 Команды
# -----------------------------

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("👋 Привет! Я бот. Используй /buy чтобы протестировать оплату.")

@dp.message(Command("add"))
async def add_student(message: Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("❌ Используй: /add Имя Группа")
        return

    name, group = parts[1], parts[2]
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO students (name, group_name) VALUES (?, ?)", (name, group))
    conn.commit()
    conn.close()

    await message.answer(f"✅ Студент {name} добавлен в группу {group}!")

@dp.message(Command("list"))
async def list_students(message: Message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, group_name FROM students")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("📭 Студентов пока нет.")
        return

    text = "📋 Список студентов:\n\n"
    for r in rows:
        text += f"#{r[0]}: {r[1]} ({r[2]})\n"

    await message.answer(text)

# -----------------------------
# 🔹 Оплата (тестовый кейс)
# -----------------------------

@dp.message(Command("buy"))
async def buy_cmd(message: Message):
    prices = [LabeledPrice(label="Подписка", amount=10000)]  # 100 = 1 рубль/тенге
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Подписка",
        description="Тестовая оплата через Telegram",
        payload="subscription_payload",
        provider_token=os.getenv("PAYMENT_TOKEN", "TEST:TOKEN"),  # ⚠️ замени на реальный
        currency="RUB",
        prices=prices,
        start_parameter="test-subscription"
    )

# Подтверждение чекаута
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Успешная оплата
@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payment = message.successful_payment
    await message.answer(
        f"✅ Оплата прошла!\n\n"
        f"Сумма: {payment.total_amount / 100} {payment.currency}\n"
        f"ID транзакции: {payment.telegram_payment_charge_id}"
    )

# -----------------------------
# 🔹 Запуск бота
# -----------------------------

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
