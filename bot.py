import asyncio
import os
from aiogram import Bot, Dispatcher, types

TOKEN = os.getenv("8875824495:AAGcaII9dC54zhTvfgbxCsgj7JIizZpThjc")

if not TOKEN:
    raise ValueError("Токен не найден! Добавь переменную TELEGRAM_BOT_TOKEN в Railway")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Я работаю!")

@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(f"Ты написал: {message.text}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
