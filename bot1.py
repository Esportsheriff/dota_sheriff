import logging
import os
import openai
import aiohttp
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.utils.exceptions import TelegramAPIError
from dotenv import load_dotenv

# Загрузка .env файла (если используется локально)
load_dotenv()

# --- Конфигурация ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# --- Инициализация бота ---
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# --- Хранилище Steam ID ---
user_steam_ids = {}

# --- Логирование ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Клавиатура ---
kb = ReplyKeyboardMarkup(resize_keyboard=True)
kb.add(KeyboardButton("📖 Как открыть профиль?"))
kb.add(KeyboardButton("🧠 Анализ последнего матча"))

# --- Обработчики ---
@dp.message_handler(commands=["start"])
async def start_handler(msg: types.Message):
    logger.info(f"/start от {msg.from_user.id}")
    instructions = (
        "👋 Привет! Я бот для анализа матчей Dota 2.\n\n"
        "🔓 Чтобы бот мог анализировать твои матчи, сделай профиль Dota 2 публичным:\n"
        "Steam → Настройки профиля → Пункт 'Игра Dota 2' → Публично\n\n"
        "1. Зайди в Dota 2\n"
        "2. Перейди в ⚙️ Раздел Сообщество\n"
        "3. Включи галочку: «Общедоступная история матчей»\n\n"
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
    user_steam_ids[msg.from_user.id] = steam_id
    logger.info(f"Steam ID {steam_id} сохранён для {msg.from_user.id}")
    await msg.reply(f"✅ Steam ID сохранён: {steam_id}\n\nТеперь ты можешь использовать команду /analyze")

@dp.message_handler(commands=["analyze"])
async def analyze_match(msg: types.Message):
    user_id = msg.from_user.id
    steam_id = user_steam_ids.get(user_id)
    if not steam_id:
        await msg.reply("⚠️ Сначала введи Steam ID с помощью команды /setsteam")
        return

    await msg.reply("🔄 Загружаем данные последнего матча...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.opendota.com/api/players/{steam_id}/matches?limit=1") as resp:
                if resp.status != 200:
                    raise Exception("Ошибка при обращении к OpenDota")
                data = await resp.json()
                if not data:
                    await msg.reply("⚠️ Не удалось получить данные. Убедись, что профиль открыт. Попробуй снова через пару минут.")
                    return
                match = data[0]
                hero_id = match.get("hero_id")
                kills = match.get("kills")
                deaths = match.get("deaths")
                assists = match.get("assists")
                result = "победа" if match.get("radiant_win") == (match.get("player_slot") < 128) else "поражение"
                summary = f"Твой последний матч: {result}. {kills}/{deaths}/{assists}. Герой: {hero_id}."

                # Отправим в OpenAI для анализа
                prompt = (
                    f"Игрок сыграл матч на герое {hero_id}. У него {kills} убийств, {deaths} смертей, {assists} ассистов. "
                    f"Результат: {result}. Сгенерируй краткий и полезный анализ его игры."
                )
                response = await openai.ChatCompletion.acreate(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}]
                )
                answer = response.choices[0].message.content
                await msg.reply(summary + "\n\n" + answer)

    except Exception as e:
        logger.exception("Ошибка при анализе матча")
        await msg.reply("Произошла ошибка при анализе матча. Попробуй позже.")

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

# --- Startup ---
async def on_startup_polling(dp):
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook удалён перед стартом polling")
    except TelegramAPIError as e:
        logger.warning(f"Не удалось удалить webhook: {e}")

# --- Запуск ---
if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup_polling, skip_updates=True)
