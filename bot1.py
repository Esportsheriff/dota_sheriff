import logging
import os
import openai
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.executor import start_webhook

# --- Конфигурация ---
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")  # Например: https://dota-sheriff.onrender.com
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 3000))  # Render автоматически задаёт PORT

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# --- Логирование ---
logging.basicConfig(level=logging.INFO)

# --- Инициализация бота ---
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# --- Клавиатура ---
kb = ReplyKeyboardMarkup(resize_keyboard=True)
kb.add(KeyboardButton("📖 Как открыть профиль?"))
kb.add(KeyboardButton("🧠 Анализ последнего матча"))

# --- Обработчики ---
@dp.message_handler(commands=["start"])
async def start_handler(msg: types.Message):
    instructions = (
        "👋 Привет! Я бот для анализа матчей Dota 2.\n\n"
        "🔓 Чтобы бот мог анализировать твои матчи, сделай профиль Dota 2 публичным:\n"
        "Steam → Настройки профиля → Пункт 'Игра Dota 2' → Публично\n\n"
        "1. Зайди в Dota 2\n"
        "2. Перейди в ⚙️ Раздел Сообщество\n"
        "4. Включи галочку: «Общедоступная история матчей»\n\n"
        "После этого введи: /setsteam [твой Steam32 ID]"
    )
    await msg.reply(instructions, reply_markup=kb)

@dp.message_handler(commands=["setsteam"])
async def set_steam_id(msg: types.Message):
    parts = msg.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.reply("⚠️ Используй формат: /setsteam 123456789")
        return
    steam_id = parts[1]
    await msg.reply(f"✅ Steam ID сохранён: {steam_id}\n\nТеперь ты можешь использовать команду /analyze")

@dp.message_handler(commands=["analyze"])
async def analyze_match(msg: types.Message):
    await msg.reply("🔄 Анализ последнего матча... (эта функция пока в разработке)")

@dp.message_handler(lambda msg: msg.text == "🧠 Анализ последнего матча")
async def analyze_button(msg: types.Message):
    await analyze_match(msg)

@dp.message_handler(lambda msg: msg.text == "📖 Как открыть профиль?")
async def profile_help(msg: types.Message):
    instructions = (
        "🔓 Чтобы бот мог анализировать твои матчи, сделай профиль Dota 2 публичным:\n\n"
        "1. Зайди в Dota 2\n"
        "2. Перейди в ⚙️ раздел Сообщество\n"
        "3. Включи галочку: «Общедоступная история матчей»\n\n"
        "После этого введи: /setsteam [твой Steam32 ID]"
    )
    await msg.reply(instructions)

# --- Webhook lifecycle ---
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    logging.info(f"Webhook set to: {WEBHOOK_URL}")

async def on_shutdown(dp):
    logging.info("Shutting down webhook...")
    await bot.delete_webhook()

# --- Запуск через Webhook ---
if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
