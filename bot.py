import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TOKEN)
# Поддержка aiogram v2
dp = Dispatcher(bot)

current_gold = 0

# Обработчик запроса от Roblox
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

# Команда /test (синтаксис aiogram v2)
@dp.message_handler(commands=['test'])
async def handle_test(message: types.Message):
    await message.reply(f"💰 Сфармлено золота: {current_gold}")

async def main():
    app = web.Application()
    app.router.add_post('/update-gold', handle_update_gold)
    
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    await site.start()
    print(f"Сервер запущен на порту {port}...")
    
    # Запуск поллинга для aiogram v2
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())
