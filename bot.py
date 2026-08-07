import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("❌ ОШИБКА: Переменная TELEGRAM_BOT_TOKEN не найдена в Railway!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

current_gold = 0

# --- ПРИЕМ ДАННЫХ ИЗ ROBLOX ---
async def handle_update_gold(request):
    global current_gold
    try:
        data = await request.json()
        if data and 'gold' in data:
            current_gold = data['gold']
            print(f"[Roblox] Обновлено золото: {current_gold}")
            return web.json_response({'status': 'success'})
    except Exception as e:
        print(f"[Roblox] Ошибка приеме данных: {e}")
    return web.json_response({'status': 'invalid payload'}, status=400)


# --- ОБРАБОТЧИКИ TELEGRAM ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    print(f"[Telegram] Команда /start от @{message.from_user.username}")
    await message.answer(
        "👋 **Привет! Я бот для отслеживания фарма в Roblox.**\n\n"
        "• Напиши `/test`, чтобы узнать количество сфармленного золота.\n"
        "• Или отправь любое сообщение!",
        parse_mode="Markdown"
    )

@dp.message(Command("test"))
async def cmd_test(message: types.Message):
    print(f"[Telegram] Команда /test от @{message.from_user.username}")
    await message.answer(
        f"💰 **Сфармлено золота:** {current_gold}", 
        parse_mode="Markdown"
    )

@dp.message()
async def handle_any_message(message: types.Message):
    print(f"[Telegram] Сообщение: '{message.text}' от @{message.from_user.username}")
    await message.answer(
        f"🤖 Бот на связи!\nВы написали: *\"{message.text}\"*\n"
        f"💰 Текущее золото: **{current_gold}**",
        parse_mode="Markdown"
    )


# --- ЗАПУСК СЕРВЕРА И БОТА ---
async def main():
    app = web.Application()
    app.router.add_post('/update-gold', handle_update_gold)
    
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"✅ HTTP-сервер запущен на порту {port}")

    try:
        me = await bot.get_me()
        print(f"✅ Бот успешно подключен к Telegram: @{me.username}")
    except Exception as e:
        print(f"❌ Ошибка подключения к Telegram: {e}")

    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 Бот полностью запущен и ожидает сообщений!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
