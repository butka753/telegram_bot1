import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище сфармленного золота
current_gold = 0

# Обработчик POST-запроса от Roblox (без Flask)
async def handle_update_gold(request):
    global current_gold
    try:
        data = await request.json()
        if data and 'gold' in data:
            current_gold = data['gold']
            return web.json_response({'status': 'success'})
    except Exception:
        pass
    return web.json_response({'status': 'invalid payload'}, status=400)

# Команда /test в Telegram
@dp.message(Command("test"))
async def handle_test(message: types.Message):
    await message.answer(f"💰 Сфармлено золота: {current_gold}")

async def main():
    # Настройка асинхронного веб-сервера aiohttp
    app = web.Application()
    app.router.add_post('/update-gold', handle_update_gold)
    
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    # Запуск веб-сервера и поллинга бота одновременно
    await site.start()
    print(f"Сервер запущен на порту {port}, бот готов...")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
