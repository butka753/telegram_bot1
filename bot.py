import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher() # В 3-й версии создается БЕЗ передаваемого бота

current_gold = 0

# Обработчик POST-запроса от Roblox
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

# Команда /test для Telegram
@dp.message(Command("test"))
async def handle_test(message: types.Message):
    await message.answer(f"💰 Сфармлено золота: {current_gold}")

async def main():
    app = web.Application()
    app.router.add_post('/update-gold', handle_update_gold)
    
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    await site.start()
    print(f"Сервер успешно запущен на порту {port}...")
    
    # Бот передается именно сюда
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
