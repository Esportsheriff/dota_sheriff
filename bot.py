import logging
import openai
import aiohttp
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- Настройки ---
TELEGRAM_TOKEN = '7646662758:AAH27KalaVNnSEM6uvRfwI_i58gwUhLK1Jg'
OPENDOTA_API = 'https://api.opendota.com/api'
OPENAI_API_KEY = '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'
openai.api_key = OPENAI_API_KEY

# --- Логирование ---
logging.basicConfig(level=logging.INFO)

# --- Бот и диспетчер ---
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# --- Клавиатура ---
kb = ReplyKeyboardMarkup(resize_keyboard=True)
kb.add(KeyboardButton("📖 Как открыть профиль?"))
kb.add(KeyboardButton("🧠 Анализ последнего матча"))

# --- Обработчики ---
@dp.message_handler(commands=["start"])
async def start_handler(msg: types.Message):
    await msg.reply("👋 Привет! Я бот для анализа матчей Dota 2.

"
                    "Отправь мне свой Steam32 ID или нажми кнопку ниже, чтобы узнать, как его получить.",
                    reply_markup=kb)

@dp.message_handler(lambda msg: msg.text == "📖 Как открыть профиль?")
async def profile_help(msg: types.Message):
    instructions = (
        "🔓 Чтобы бот мог анализировать твои матчи, сделай профиль Dota 2 публичным:
"
        "Steam → Настройки профиля → Пункт 'Игра Dota 2' → Публично

"
        "1. Зайди в Dota 2
"
        "2. Нажми на свой профиль (вверху)
"
        "3. Перейди в⚙️ Настройки профиля
"
        "4. Включи галочку: «Сделать профиль публичным»

"
        "После этого введи: /setsteam [твой Steam32 ID]"
    )
    await msg.reply(instructions)

@dp.message_handler(commands=["setsteam"])
async def set_steam_id(msg: types.Message):
    parts = msg.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.reply("⚠️ Используй формат: /setsteam 123456789")
        return
    steam_id = parts[1]
    await msg.reply(f"✅ Steam ID сохранён: {steam_id}

Теперь ты можешь использовать команду /analyze")

@dp.message_handler(commands=["analyze"])
async def analyze_match(msg: types.Message):
    await msg.reply("🔄 Анализ последнего матча... (эта функция пока в разработке)")

@dp.message_handler(lambda msg: msg.text == "🧠 Анализ последнего матча")
async def analyze_button(msg: types.Message):
    await analyze_match(msg)

# --- Запуск ---
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
