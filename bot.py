import asyncio
import html
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATA_FILE = "database.json"

if not TOKEN:
    print("❌ ОШИБКА: Переменная TELEGRAM_BOT_TOKEN не найдена!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- РАБОТА С ХРАНИЛИЩЕМ (JSON) ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Ошибка при чтении {DATA_FILE}: {e}")
    return {"gold": {}, "links": {}}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Ошибка при сохранении {DATA_FILE}: {e}")

# Загружаем базу при старте
db = load_data()

# --- ПРИЕМ ДАННЫХ ИЗ ROBLOX ---
async def handle_update_gold(request):
    try:
        data = await request.json()
        username = data.get('username')
        gold = data.get('gold')

        if username and gold is not None:
            db["gold"][str(username)] = int(gold)
            save_data(db)
            print(f"[Roblox] Игрок '{username}': золото -> {gold}")
            return web.json_response({'status': 'success', 'username': username, 'gold': gold})
        else:
            return web.json_response({'status': 'error', 'message': 'Missing username or gold'}, status=400)
    except Exception as e:
        print(f"[Roblox] Ошибка приема данных: {e}")
        return web.json_response({'status': 'invalid payload'}, status=400)


# --- КОМАНДЫ TELEGRAM ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    tg_id = str(message.from_user.id)
    linked_nick = db["links"].get(tg_id)

    msg = (
        "👋 <b>Привет! Я бот для отслеживания фарма в Roblox.</b>\n\n"
        "📌 <b>Как пользоваться:</b>\n"
        "1️⃣ Привяжи свой Roblox никнейм командой:\n"
        "   <code>/link ТвойНикRoblox</code>\n"
        "2️⃣ Напиши <code>/test</code>, чтобы проверить баланс.\n"
        "3️⃣ Команда <code>/top</code> покажет топ игроков.\n"
    )
    if linked_nick:
        safe_nick = html.escape(str(linked_nick))
        msg += f"\n✅ Ваш текущий Roblox ник: <b>{safe_nick}</b>"
    else:
        msg += "\n⚠️ У вас еще не привязан ник. Привяжите его через <code>/link</code>."

    await message.answer(msg, parse_mode="HTML")


@dp.message(Command("link"))
async def cmd_link(message: types.Message, command: CommandObject):
    if not command.args:
        await message.answer("⚠️ <b>Укажите ваш Roblox никнейм!</b>\nПример: <code>/link Builderman</code>", parse_mode="HTML")
        return

    roblox_username = command.args.strip()
    tg_id = str(message.from_user.id)
    
    db["links"][tg_id] = roblox_username
    save_data(db)

    gold = db["gold"].get(roblox_username, 0)
    safe_nick = html.escape(roblox_username)
    
    await message.answer(
        f"✅ Успешно привязан Roblox аккаунт: <b>{safe_nick}</b>\n\n"
        f"💰 Текущее сфармленное золото: <b>{gold}</b>\n"
        f"Проверяйте баланс в любой момент командой <code>/test</code>.",
        parse_mode="HTML"
    )


@dp.message(Command("test", "mygold"))
async def cmd_test(message: types.Message):
    tg_id = str(message.from_user.id)
    linked_nick = db["links"].get(tg_id)

    if not linked_nick:
        await message.answer(
            "⚠️ Вы еще не привязали ваш Roblox ник!\n"
            "Напишите: <code>/link ВашНикRoblox</code>",
            parse_mode="HTML"
        )
        return

    gold = db["gold"].get(linked_nick, 0)
    safe_nick = html.escape(str(linked_nick))
    await message.answer(
        f"👤 Аккаунт Roblox: <b>{safe_nick}</b>\n"
        f"💰 Сфармлено золота: <b>{gold}</b>",
        parse_mode="HTML"
    )


@dp.message(Command("top"))
async def cmd_top(message: types.Message):
    if not db["gold"]:
        await message.answer("📊 Данных о золоте пока нет.")
        return

    sorted_top = sorted(db["gold"].items(), key=lambda x: x[1], reverse=True)[:10]
    text = "🏆 <b>Топ игроков по золоту:</b>\n\n"
    for i, (nick, gold) in enumerate(sorted_top, start=1):
        safe_nick = html.escape(str(nick))
        text += f"{i}. <b>{safe_nick}</b>: {gold} 💰\n"

    await message.answer(text, parse_mode="HTML")


@dp.message()
async def handle_any_message(message: types.Message):
    tg_id = str(message.from_user.id)
    linked_nick = db["links"].get(tg_id)

    if linked_nick:
        safe_nick = html.escape(str(linked_nick))
        gold = db["gold"].get(linked_nick, 0)
        gold_info = f"\n👤 Ник: <b>{safe_nick}</b>\n💰 Золото: <b>{gold}</b>"
    else:
        gold_info = "\n⚠️ Ник не привязан. Используйте <code>/link ВашНик</code>"

    safe_text = html.escape(message.text or "")
    await message.answer(
        f"🤖 Бот на связи!\nВы написали: <i>\"{safe_text}\"</i>{gold_info}",
        parse_mode="HTML"
    )


# --- ЗАПУСК ---
async def main():
    app = web.Application()
    app.router.add_post('/update-gold', handle_update_gold)

    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"✅ HTTP-сервер запущен на порту {port}")

    # Удаляем вебхуки и сбрасываем очереди, чтобы избежать ошибок
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        me = await bot.get_me()
        print(f"✅ Бот успешно подключен к Telegram: @{me.username}")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

    print("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
