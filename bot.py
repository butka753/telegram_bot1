import asyncio
import json
import os
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta

# --- Получение и очистка токена ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("❌ ОШИБКА: Переменная TELEGRAM_BOT_TOKEN не найдена!")
    exit(1)

TOKEN = TOKEN.strip()

if len(TOKEN) < 30:
    print(f"❌ ОШИБКА: Токен слишком короткий ({len(TOKEN)} символов)")
    exit(1)

print(f"✅ Токен получен: {TOKEN[:10]}...{TOKEN[-5:]}")

# --- Инициализация ---
DATA_FILE = "database.json"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Словарь для хранения времени последнего нажатия (КД)
cooldown = {}

# --- Функции для работы с базой данных ---

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_score(user_id: int) -> int:
    data = load_data()
    return data["users"].get(str(user_id), 0)

def update_user_score(user_id: int, points: int):
    data = load_data()
    user_id_str = str(user_id)
    data["users"][user_id_str] = data["users"].get(user_id_str, 0) + points
    save_data(data)

# --- Команды ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    score = get_user_score(user_id)
    
    keyboard = [
        [InlineKeyboardButton(text="🎲 Кости", callback_data="dice")],
        [InlineKeyboardButton(text="🎰 Казино", callback_data="casino")],
        [InlineKeyboardButton(text="🏀 Баскетбол", callback_data="basketball")],
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await message.answer(
        f"🎮 Привет, {message.from_user.first_name}!\n"
        f"💰 Твой счёт: {score} очков.\n\n"
        f"Выбери игру:",
        reply_markup=reply_markup
    )

@dp.message(Command("score"))
async def cmd_score(message: types.Message):
    user_id = message.from_user.id
    score = get_user_score(user_id)
    await message.answer(f"💰 Твой текущий счёт: {score} очков.")

@dp.message(Command("leaderboard"))
async def cmd_leaderboard(message: types.Message):
    data = load_data()
    users = data.get("users", {})
    
    if not users:
        await message.answer("📊 Пока нет игроков в таблице лидеров!")
        return
    
    sorted_users = sorted(users.items(), key=lambda x: x[1], reverse=True)
    top_users = sorted_users[:10]
    
    leaderboard_text = "🏆 ТАБЛИЦА ЛИДЕРОВ 🏆\n\n"
    for i, (user_id, score) in enumerate(top_users, 1):
        try:
            user = await bot.get_chat(int(user_id))
            name = user.first_name or f"User_{user_id}"
        except:
            name = f"User_{user_id}"
        
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        leaderboard_text += f"{medal} {name} — {score} очков\n"
    
    await message.answer(leaderboard_text)

@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    user_id = message.from_user.id
    data = load_data()
    user_id_str = str(user_id)
    
    if user_id_str in data["users"]:
        data["users"][user_id_str] = 0
        save_data(data)
        await message.answer("🔄 Твой счёт сброшен до 0!")
    else:
        await message.answer("❌ У тебя и так 0 очков!")

# --- Обработчик игр (КНОПКИ) ---

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    game = callback.data
    
    # --- Проверка КД (3 секунды) ---
    now = datetime.now()
    if user_id in cooldown:
        time_diff = (now - cooldown[user_id]).total_seconds()
        if time_diff < 3:
            remaining = 3 - time_diff
            await callback.answer(f"⏳ Подожди {remaining:.1f} сек!", show_alert=False)
            return
    
    # Обновляем время последнего нажатия
    cooldown[user_id] = now
    
    print(f"🔔 Нажата кнопка: {game} от пользователя {user_id}")
    
    current_score = get_user_score(user_id)
    points = 0
    result_text = ""
    emoji_message = None
    
    # --- ИГРА В КОСТИ (с реальным эмодзи) ---
    if game == "dice":
        # Отправляем анимированный кубик
        dice_message = await callback.message.answer_dice(emoji="🎲")
        value = dice_message.dice.value
        
        dice_emoji = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        result_text = f"🎲 Выпало: {dice_emoji[value]} ({value})"
        
        if value == 6:
            points = 2
            result_text += "\n🎉 Поздравляю! Ты выиграл 2 очка!"
        else:
            result_text += "\n😕 Попробуй ещё раз!"
            
    # --- ИГРА В КАЗИНО (слот) ---
    elif game == "casino":
        # Отправляем анимированный слот
        slot_message = await callback.message.answer_dice(emoji="🎰")
        value = slot_message.dice.value  # 1-6 для слота (или другое значение)
        
        # Для слота значения от 1 до 6, эмулируем 777
        # Если выпало 6 - считаем как 777
        result_text = f"🎰 Результат: {value}"
        
        if value == 6:  # Джекпот (эмуляция 777)
            points = 10
            result_text += "\n🎉 ДЖЕКПОТ! Ты выиграл 10 очков!"
        elif value >= 4:  # Хороший результат
            points = 2
            result_text += "\n✨ Хороший результат! +2 очка."
        else:
            result_text += "\n😕 Не повезло, попробуй ещё!"
            
    # --- ИГРА В БАСКЕТБОЛ ---
    elif game == "basketball":
        # Отправляем анимированный баскетбол
        basket_message = await callback.message.answer_dice(emoji="🏀")
        value = basket_message.dice.value  # 1-6 для баскетбола
        
        # В баскетболе значение 4-6 - попадание, 1-3 - промах
        result_text = f"🏀 Бросок..."
        
        if value >= 4:  # Попадание
            points = 2
            result_text = "🏀🏆 Ты попал в корзину! +2 очка!"
        else:
            result_text = "🏀❌ Промах! Попробуй ещё раз."
    
    # Обновляем счёт
    if points > 0:
        update_user_score(user_id, points)
        new_score = get_user_score(user_id)
    else:
        new_score = current_score
    
    # Обновляем клавиатуру
    keyboard = [
        [InlineKeyboardButton(text="🎲 Кости", callback_data="dice")],
        [InlineKeyboardButton(text="🎰 Казино", callback_data="casino")],
        [InlineKeyboardButton(text="🏀 Баскетбол", callback_data="basketball")],
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Отвечаем на callback
    await callback.answer()
    
    # Редактируем исходное сообщение (меню)
    await callback.message.edit_text(
        text=f"{result_text}\n\n💰 Твой счёт: {new_score} очков.\n\nВыбери следующую игру:",
        reply_markup=reply_markup
    )

# --- ЗАПУСК ---

async def main():
    print("🤖 Бот запущен на Railway с ПОЛЛИНГОМ!")
    print("📁 Данные сохраняются в:", DATA_FILE)
    print("🔄 Начинаем polling...")
    print("⏳ КД между нажатиями: 3 секунды")
    
    # Удаляем старый webhook (если был)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
