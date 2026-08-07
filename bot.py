from aiogram import Bot, Dispatcher, types
import asyncio
import os

TOKEN = os.getenv("8875824495:AAGcaII9dC54zhTvfgbxCsgj7JIizZpThjc")

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message()
async def echo(message: types.Message):
    await message.answer(f"Ты сказал: {message.text}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())