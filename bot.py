import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: Переменная TELEGRAM_BOT_TOKEN пустая! Проверьте Variables в Railway.")

bot = Bot(token=TOKEN)
dp = Dispatcher()

current_gold = 0

@app_route := "/update-gold"

async def handle_update_gold(request):
    global current_gold
    try:
        data = await request.json()
        if data and 'gold' in data:
            current_gold = data['gold']
            print(f"[Roblox] Обновлено золото: {current_gold}")
            return web.json_response({'status': 'success'})
    except Exception as e:
        print(f"[Roblox] Ошибка: {e}")
    return web.json_response({'status': 'invalid payload'}, status=400)

# Реагирует на ВСЕ текстовые сообщения
@dp.message()
async def echo_all(message: types.Message):
    print(f"📩 ПОЛУЧЕНО СООБЩЕНИЕ: {message.text} от @{message.from_user.username}")
    await message.answer(f"Бот работает! Вы написали: {message.text}\nТекущее золото: {current_gold}")

async def main():
    try:
        me = await bot.get_me()
        print(f"----------------------------------------")
        print(f"🤖 УСПЕШНЫЙ ЗАПУСК! Бот: @{me.username}")
        print(f"----------------------------------------")
    except Exception as e:
        print(f"❌ Ошибка авторизации бота (проверьте токен): {e}")
        return

    app = web.Application()
    app.router.add_post('/update-gold', handle_update_gold)
    
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    await site.start()
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
