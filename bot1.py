import logging
import os
import openai
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

# --- Конфигурация ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

# --- Логирование ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Инициализация бота ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# --- Временное хранилище Steam ID ---
steam_ids = {}

# --- Клавиатура ---
kb = ReplyKeyboardMarkup(resize_keyboard=True)
kb.add(KeyboardButton("📖 Как открыть профиль?"))
kb.add(KeyboardButton("🧠 Анализ последнего матча"))

# --- Обработчики ---
@dp.message_handler(commands=["start"])
async def start_handler(msg: types.Message):
    logger.info(f"/start от {msg.from_user.id}")
    await msg.reply(
        "Привет! Я бот для анализа матчей Dota 2.\n\n"
        "Сделай профиль публичным и введи /setsteam <твой Steam32 ID>.",
        reply_markup=kb
    )

@dp.message_handler(commands=["setsteam"])
async def set_steam_id(msg: types.Message):
    parts = msg.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.reply("⚠️ Используй формат: /setsteam 123456789")
        return
    steam_id = parts[1]
    steam_ids[msg.from_user.id] = steam_id
    logger.info(f"Steam ID {steam_id} сохранён для {msg.from_user.id}")
    await msg.reply(f"✅ Steam ID сохранён: {steam_id}\nТеперь можешь использовать /analyze")

@dp.message_handler(commands=["analyze"])
async def analyze_match(msg: types.Message):
    user_id = msg.from_user.id
    steam_id = steam_ids.get(user_id)
    if not steam_id:
        await msg.reply("⚠️ Сначала введи свой Steam ID через /setsteam")
        return

    await msg.reply("🔄 Загружаю матч...")

    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.opendota.com/api/players/{steam_id}/recentMatches"
            async with session.get(url) as r:
                matches = await r.json()

            if not matches:
                await msg.reply("⚠️ Не найдено матчей. Убедись, что профиль открыт и история матчей доступна. Попробуй снова через пару минут.")
                return

            match_id = matches[0]['match_id']
            url = f"https://api.opendota.com/api/matches/{match_id}"
            async with session.get(url) as r:
                match_data = await r.json()

        player_data = next((p for p in match_data.get("players", []) if str(p.get("account_id")) == steam_id), None)
        if not player_data:
            await msg.reply("⚠️ Не найден игрок в матче.")
            return

        summary = (
            f"Герой: {player_data.get('hero_id')}\n"
            f"K/D/A: {player_data['kills']}/{player_data['deaths']}/{player_data['assists']}\n"
            f"Урон: {player_data['hero_damage']}, Золото: {player_data['total_gold']}"
        )

        prompt = (
            "Ты эксперт по Dota 2. Проанализируй игру игрока, выдай краткий разбор, советы и ошибки.\n\n"
            f"Данные:\n{summary}"
        )

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты аналитик по Dota 2."},
                {"role": "user", "content": prompt}
            ]
        )

        analysis = response.choices[0].message.content.strip()
        await msg.reply(f"🧪 Анализ:\n{analysis}")

    except Exception as e:
        logger.exception("Ошибка анализа")
        await msg.reply("❌ Произошла ошибка во время анализа матча.")

@dp.message_handler(lambda msg: msg.text == "🧠 Анализ последнего матча")
async def analyze_button(msg: types.Message):
    await analyze_match(msg)

@dp.message_handler(lambda msg: msg.text == "📖 Как открыть профиль?")
async def profile_help(msg: types.Message):
    await msg.reply(
        "1. Steam → Настройки → Игра Dota 2 → Публично\n"
        "2. В Dota 2: Сообщество → Общедоступная история матчей\n"
        "3. Введи команду: /setsteam <Steam32 ID>"
    )

# --- Запуск через Polling ---
if __name__ == "__main__":
    logger.info("Starting bot in polling mode...")
    executor.start_polling(dp, skip_updates=True)
