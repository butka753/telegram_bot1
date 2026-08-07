import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("❌ ОШИБКА: Переменная TELEGRAM_BOT_TOKEN не найдена в Railway!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилища в памяти
# roblox_gold: {"RobloxUsername": 1000}
roblox_gold = {}

# telegram_links: {telegram_user_id: "RobloxUsername"}
telegram_links = {}

# --- ПРИЕМ ДАННЫХ ИЗ ROBLOX ---
async def handle_update_gold(request):
    try:
        data = await request.json()
        # Ожидаем JSON: {"username": "ИмяИгрока", "gold": 500}
        username = data.get('username')
        gold = data.get('gold')

        if username and gold is not None:
            roblox_gold[str(username)] = int(gold)
            print(f"[Roblox] Игрок '{username}': обновлено золото -> {gold}")
            return web.json_response({'status': 'success', 'username': username, 'gold': gold})
        else:
            return web.json_response({'status': 'error', 'message': 'Missing username or gold'}, status=400)
    except Exception as e:
        print(f"[Roblox] Ошибка приема данных: {e}")
        return web.json_response({'status': 'invalid payload'}, status=400)


# --- ОБРАБОТЧИКИ TELEGRAM ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    tg_id = message.from_user.id
    linked_nick = telegram_links.get(tg_id)

    msg = (
        "👋 **Привет! Я бот для отслеживания фарма в Roblox.**\n\n"
        "📌 **Как пользоваться:**\n"
        "1️⃣ Привяжи свой Roblox никнейм командой:\n"
        "   `/link ТвойНикRoblox`\n"
        "2️⃣ Напиши `/test` или `/mygold`, чтобы проверить баланс.\n"
        "3️⃣ Команда `/top` покажет топ игроков.\n"
    )
    if linked_nick:
        msg += f"\n✅ Ваш текущий Roblox ник: **{linked_nick}**"
    else:
        msg += "\n⚠️ У вас еще не привязан ник. Привяжите его через `/link`."

    await message.answer(msg, parse_mode="Markdown")


@dp.message(Command("link"))
async def cmd_link(message: types.Message, command: CommandObject):
    if not command.args:
        await message.answer("⚠️ **Укажите ваш Roblox никнейм!**\nПример: `/link Builderman`", parse_mode="Markdown")
        return

    roblox_username = command.args.strip()
    telegram_links[message.from_user.id] = roblox_username

    gold = roblox_gold.get(roblox_username, 0)
    await message.answer(
        f"✅ Успешно привязан Roblox аккаунт: **{roblox_username}**\n\n"
        f"💰 Текущее сфармленное золото: **{gold}**\n"
        f"Проверяйте баланс в любой момент командой `/test`.",
        parse_mode="Markdown"
    )


@dp.message(Command("test", "mygold"))
async def cmd_test(message: types.Message):
    tg_id = message.from_user.id
    linked_nick = telegram_links.get(tg_id)

    if not linked_nick:
        await message.answer(
            "⚠️ Вы еще не привязали ваш Roblox ник!\n"
            "Напишите: `/link ВашНикRoblox` (например, `/link Player123`).",
            parse_mode="Markdown"
        )
        return

    gold = roblox_gold.get(linked_nick, 0)
    await message.answer(
        f"👤 Аккаунт Roblox: **{linked_nick}**\n"
        f"💰 Сфармлено золота: **{gold}**",
        parse_mode="Markdown"
    )


@dp.message(Command("top"))
async def cmd_top(message: types.Message):
    if not roblox_gold:
        await message.answer("📊 Данных о золоте пока нет.")
        return

    sorted_top = sorted(roblox_gold.items(), key=lambda x: x[1], reverse=True)[:10]
    text = "🏆 **Топ игроков по золоту:**\n\n"
    for i, (nick, gold) in enumerate(sorted_top, start=1):
        text += f"{i}. **{nick}**: {gold} 💰\n"

    await message.answer(text, parse_mode="Markdown")


@dp.message()
async def handle_any_message(message: types.Message):
    tg_id = message.from_user.id
    linked_nick = telegram_links.get(tg_id)

    if linked_nick:
        gold = roblox_gold.get(linked_nick, 0)
        gold_info = f"\n👤 Ник: **{linked_nick}**\n💰 Золото: **{gold}**"
    else:
        gold_info = "\n⚠️ Ник не привязан. Используйте `/link ВашНик`"

    await message.answer(
        f"🤖 Бот на связи!\nВы написали: *\"{message.text}\"*{gold_info}",
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
