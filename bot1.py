# Updated bot code with webhook support and improved auto-reconnect behavior
import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import TelegramAPIError
from dotenv import load_dotenv
import aiohttp
import asyncio

load_dotenv()

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.reply("Привет! Пришли мне свой Steam ID или профиль.")

async def on_startup(dispatcher):
    try:
        await bot.delete_webhook()
        logger.info("Webhook удалён перед стартом polling")
    except TelegramAPIError as e:
        logger.warning(f"Ошибка удаления webhook: {e}")

async def main():
    try:
        await on_startup(dp)
        await dp.start_polling()
    except Exception as e:
        logger.exception(f"Ошибка при запуске polling: {e}")
        await asyncio.sleep(10)
        await main()  # Рекурсивный перезапуск при падении

if __name__ == '__main__':
    asyncio.run(main())
