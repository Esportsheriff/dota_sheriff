import logging
import os
import openai
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.executor import start_webhook

# --- Конфигурация ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 3000))

openai.api_key = OPENAI_API_KEY

# --- Логирование ---
logging.basicConfig(level=logging.INFO)

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
    instructions = (
        "Привет! Я бот для анализа матчей Dota 2.\n\n"
        "Чтобы начать, сделай свой профиль публичным:\n"
        "Steam → Настройки → Игра Dota 2 → Публично\n\n"
        "Потом введи команду: /setsteam <твой Steam32 ID>"
    )
    await msg.reply(instructions, reply_markup=kb)

@dp.message_handler(commands=["setsteam"])
async def set_steam_id(msg: types.Message):
    parts = msg.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.reply("⚠️ Используй формат: /setsteam 123456789")
        return
    steam_id = parts[1]
    steam_ids[msg.from_user.id] = steam_id
    await msg.reply(f"✅ Steam ID сохранён: {steam_id}\n\nТеперь ты можешь использовать команду /analyze")

@dp.message_handler(commands=["analyze"])
async def analyze_match(msg: types.Message):
    user_id = msg.from_user.id
    steam_id = steam_ids.get(user_id)
    if not steam_id:
        await msg.reply("⚠️ Сначала введи свой Steam ID через /setsteam")
        return

    await msg.reply("🔄 Загружаю данные последнего матча...")

    try:
        async with aiohttp.ClientSession() as session:
            recent_url = f"https://api.opendota.com/api/players/{steam_id}/recentMatches"
            async with session.get(recent_url) as r:
                recent_matches = await r.json()
            if not recent_matches:
                await msg.reply("⚠️ Матчи не найдены.")
                return
            last_match_id = recent_matches[0]['match_id']

            match_url = f"https://api.opendota.com/api/matches/{last_match_id}"
            async with session.get(match_url) as r:
                match_data = await r.json()

        player_data = next((p for p in match_data.get("players", []) if str(p.get("account_id")) == steam_id), None)
        if not player_data:
            await msg.reply("⚠️ Не удалось найти игрока в матче.")
            return

        summary = (
            f"Герой: {player_data.get('hero_id')}\n"
            f"K/D/A: {player_data['kills']}/{player_data['deaths']}/{player_data['assists']}\n"
            f"Net Worth: {player_data['total_gold']} золота\n"
            f"Урон по героям: {player_data['hero_damage']}\n"
            f"Линия: {player_data.get('lane', 'N/A')}\n"
            f"Победа: {'Да' if player_data.get('win') else 'Нет'}"
        )

        prompt = (
            "Ты аналитик Dota 2. Проанализируй игру этого игрока, выдай краткий, но глубокий разбор, ошибки и советы."
            f"\n\nСтатистика матча:\n{summary}"
        )

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты эксперт по Dota 2 и анализу матчей."},
                {"role": "user", "content": prompt}
            ]
        )

        analysis = response.choices[0].message.content.strip()
        await msg.reply(f"🧪 Анализ:\n{analysis}")

    except Exception as e:
        logging.exception("Ошибка при анализе матча")
        await msg.reply("❌ Произошла ошибка при анализе матча.")

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
        "После этого введи: /setsteam <твой Steam32 ID>"
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
