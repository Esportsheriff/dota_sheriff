import requests
import openai
import logging
import json
import os
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# --- Настройки ---
TELEGRAM_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
OPENDOTA_API = 'https://api.opendota.com/api'
OPENAI_API_KEY = 'YOUR_OPENAI_API_KEY'
openai.api_key = OPENAI_API_KEY
USER_DB_PATH = 'user_steam_ids.json'

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

# --- Имитация БД ---
def load_user_ids():
    if os.path.exists(USER_DB_PATH):
        with open(USER_DB_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_user_ids(data):
    with open(USER_DB_PATH, 'w') as f:
        json.dump(data, f)

user_steam_ids = load_user_ids()
unlocked_users = set(user_steam_ids.keys())

# --- UI Команды ---
@dp.message_handler(commands=['start'])
async def welcome(msg: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("👤 Привязать свой Steam ID"))
    if str(msg.from_user.id) in user_steam_ids:
        keyboard.add(KeyboardButton("🎮 Последние 10 матчей"))
    keyboard.add(KeyboardButton("📊 Разбор по ID матча и герою"))
    keyboard.add(KeyboardButton("📖 Как открыть профиль?"))
    await msg.reply("Добро пожаловать! Выбери действие:", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "👤 Привязать свой Steam ID")
async def prompt_bind(msg: types.Message):
    await msg.reply("Введи Steam32 ID (например: /setsteam 90665163)")

@dp.message_handler(lambda msg: msg.text == "📖 Как открыть профиль?")
async def profile_help(msg: types.Message):
    instructions = (
        "🔓 Чтобы бот мог анализировать твои матчи, сделай профиль Dota 2 публичным:

"
        "1. Зайди в Dota 2
"
        "2. Нажми на свой профиль (вверху)
"
        "3. Перейди в ⚙️ Настройки профиля
"
        "4. Включи галочку: «Сделать профиль публичным»

"
        "После этого введи: /setsteam [твой Steam32 ID]"
    )
    await msg.reply(instructions)

@dp.message_handler(commands=['setsteam'])
async def set_steam(msg: types.Message):
    try:
        steam_id = int(msg.text.split()[1])
        check = requests.get(f"{OPENDOTA_API}/players/{steam_id}")
        if check.status_code == 200 and 'profile' in check.json():
            user_steam_ids[str(msg.from_user.id)] = steam_id
            save_user_ids(user_steam_ids)
            await msg.reply(f"✅ Профиль открыт и сохранён! Steam ID: {steam_id}")
        else:
            await msg.reply("🔒 Профиль закрыт. Открой его в Dota 2 (нажми '📖 Как открыть профиль?') для работы бота.")
    except:
        await msg.reply("⚠️ Формат: /setsteam 123456789")

@dp.message_handler(lambda msg: msg.text == "🎮 Последние 10 матчей")
async def last10_matches(msg: types.Message):
    user_id = str(msg.from_user.id)
    if user_id not in user_steam_ids:
        await msg.reply("Сначала укажи свой Steam ID командой /setsteam")
        return

    steam_id = user_steam_ids[user_id]
    url = f"{OPENDOTA_API}/players/{steam_id}/matches?limit=10"
    resp = requests.get(url)
    if resp.status_code != 200:
        await msg.reply("Не удалось получить матчи. Попробуй позже.")
        return

    matches = resp.json()
    if not matches:
        await msg.reply("Нет матчей для отображения.")
        return

    for m in matches:
        match_id = m.get("match_id")
        kills = m.get("kills", 0)
        deaths = m.get("deaths", 0)
        assists = m.get("assists", 0)
        kda = f"{kills}/{deaths}/{assists}"
        win = "✅ Win" if (m["radiant_win"] and m["player_slot"] < 128) or (not m["radiant_win"] and m["player_slot"] >= 128) else "❌ Loss"
        caption = f"{win} | Match ID: {match_id} | KDA: {kda}"

        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(f"📊 Разобрать {match_id}", callback_data=f"analyze_{match_id}")
        )
        await msg.reply(caption, reply_markup=kb)

@dp.callback_query_handler(lambda call: call.data.startswith("analyze_"))
async def inline_analyze(call: types.CallbackQuery):
    match_id = call.data.split("_")[1]
    user_id = str(call.from_user.id)
    steam_id = user_steam_ids.get(user_id)

    await call.message.answer(f"🔍 Анализирую матч {match_id}...")

    data = get_match_data(match_id)
    if not data or not steam_id:
        await call.message.answer("⚠️ Не удалось получить данные.")
        return

    player = find_player(data, user_id=user_id)
    if not player:
        await call.message.answer("❌ Не найден игрок по Steam ID.")
        return

    try:
        summary = generate_ai_player_summary(player, match_id)
    except Exception as e:
        logging.warning(f"GPT fallback: {e}")
        summary = f"Играл {player.get('personaname', 'аноним')}, умер {player['deaths']} раз, GPM {player['gold_per_min']} — ну ты понял…"

    await call.message.answer(summary)

@dp.message_handler(lambda msg: ':' in msg.text)
async def analyze_with_gpt(msg: types.Message):
    parts = msg.text.split(':')
    match_id = parts[0]
    hero_name = parts[1]

    await msg.reply("🔍 Ищу матч и готовлю разбор...")

    data = get_match_data(match_id)
    if not data:
        await msg.reply("❌ Не удалось получить данные. Проверь Match ID.")
        return

    player = find_player(data, msg.from_user.id, hero_name)
    if not player:
        await msg.reply("❌ Не найден игрок. Проверь героя или ID.")
        return

    try:
        summary = generate_ai_player_summary(player, match_id)
    except Exception as e:
        logging.warning(f"GPT fallback: {e}")
        summary = f"Играл {player.get('personaname', 'аноним')}, умер {player['deaths']} раз, GPM {player['gold_per_min']} — ну ты понял…"

    await msg.reply(summary)

# --- Вспомогательные функции ---
def get_match_data(match_id):
    url = f"{OPENDOTA_API}/matches/{match_id}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

def find_player(data, user_id=None, hero_name=None):
    if hero_name:
        for p in data['players']:
            if p.get('hero_name', '').lower() == hero_name.lower():
                return p
    if user_id and str(user_id) in user_steam_ids:
        steam32 = user_steam_ids[str(user_id)]
        for p in data['players']:
            if p.get('account_id') == steam32:
                return p
    return None

def build_gpt_prompt(player, match_id):
    prompt = f'''
Ты — саркастичный, но умный Dota 2 тренер. Я передаю тебе JSON-данные одного игрока в матче. 
Дай общий вердикт, укажи ключевые ошибки (по таймингам), и хорошие моменты. Тон язвительный и меткий.
Вот JSON игрока из матча ID {match_id}: {json.dumps(player, ensure_ascii=False)}
'''
    return prompt.strip()

def generate_ai_player_summary(player, match_id):
    prompt = build_gpt_prompt(player, match_id)
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Ты — язвительный аналитик Dota 2."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.9,
        max_tokens=900,
        timeout=20
    )
    return response['choices'][0]['message']['content']

# --- Запуск ---
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)