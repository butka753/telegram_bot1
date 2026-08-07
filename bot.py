import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("❌ ОШИБКА: Переменная TELEGRAM_BOT_TOKEN не найдена в Railway!")

bot = Bot(token=TOKEN)
dp = Dispatcher()  # СТРОГО БЕЗ bot В СКОБКАХ

current_gold = 0

# Прием данных из Roblox
async def handle_update_gold(request):
    global current_gold
    try:
        data = await request.json()
        if data and 'gold' in data:
            current_gold = data['gold']
            print(f"[Roblox] Обновлено золото: {current_gold}")
            return web.json_response({'status': 'success'})
    except Exception as e:
        print(f"[Roblox] Ошибка приема данных: {e}")
    return web.json_response({'status': 'invalid payload'}, status=400)

# Команда /test в Telegram
@dp.message(Command("test"))
async def handle_test(message: types.Message):
    print(f"[Telegram] Получена команда /test от ID: {message.from_user.id}")
    await message.answer(f"💰 Сфармлено золота: {current_gold}")

async def main():
    app = web.Application()
    app.router.add_post('/update-gold', handle_update_gold)
    
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    await site.start()
    print(f"✅ HTTP-сервер запущен на порту {port}")
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Бот готов принимать сообщения в Telegram!")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
