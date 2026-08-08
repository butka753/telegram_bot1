import asyncio
import html
import json
import os
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiohttp import web

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATA_FILE = "database.json"

if not TOKEN:
    print("❌ ОШИБКА: Переменная TELEGRAM_BOT_TOKEN не найдена!")
    exit()

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- Функции для работы с базой данных (JSON) ---

def load_data():
    """Загружает данные из JSON файла"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}}  # структура: {"users": {"user_id": score, ...}}

def save_data(data):
    """Сохраняет данные в JSON файл"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_score(user_id: int) -> int:
    """Получает счёт пользователя"""
    data = load_data()
    return data["users"].get(str(user_id), 0)

def update_user_score(user_id: int, points: int):
    """Обновляет счёт пользователя (добавляет очки)"""
    data = load_data()
    user_id_str = str(user_id)
    data["users"][user_id_str] = data["users"].get(user_id_str, 0) + points
    save_data(data)

# --- Команда /start ---

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

# --- Команда /score ---

@dp.message(Command("score"))
async def cmd_score(message: types.Message):
    user_id = message.from_user.id
    score = get_user_score(user_id)
    await message.answer(f"💰 Твой текущий счёт: {score} очков.")

# --- Обработчик нажатий на кнопки ---

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    game = callback.data
    
    # Получаем текущий счёт
    current_score = get_user_score(user_id)
    points = 0
    result_text = ""
    
    if game == "dice":
        # Бросок кубика
        value = random.randint(1, 6)
        dice_emoji = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        result_text = f"🎲 Выпало: {dice_emoji[value]} ({value})"
        
        if value == 6:
            points = 2
            result_text += "\n🎉 Поздравляю! Ты выиграл 2 очка!"
        else:
            result_text += "\n😕 Попробуй ещё раз!"
            
    elif game == "casino":
        # Казино (имитация слота)
        value = random.randint(0, 9)
        result_text = f"🎰 Результат: {value}"
        
        if value == 7:
            points = 10
            result_text += "\n🎉 ДЖЕКПОТ! Ты выиграл 10 очков!"
        elif value % 2 == 0 and value != 0:
            points = 1
            result_text += "\n✨ Бонус за чётное число: +1 очко."
        else:
            result_text += "\n😕 Не повезло, попробуй ещё!"
            
    elif game == "basketball":
        # Баскетбол (60% попадания)
        if random.random() < 0.6:
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
    
    # Показываем результат и обновлённое меню
    keyboard = [
        [InlineKeyboardButton(text="🎲 Кости", callback_data="dice")],
        [InlineKeyboardButton(text="🎰 Казино", callback_data="casino")],
        [InlineKeyboardButton(text="🏀 Баскетбол", callback_data="basketball")],
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Отвечаем на callback (убираем "часики")
    await callback.answer()
    
    # Редактируем сообщение с результатом
    await callback.message.edit_text(
        text=f"{result_text}\n\n💰 Твой счёт: {new_score} очков.\n\nВыбери следующую игру:",
        reply_markup=reply_markup
    )

# --- Команда /leaderboard (топ игроков) ---

@dp.message(Command("leaderboard"))
async def cmd_leaderboard(message: types.Message):
    data = load_data()
    users = data.get("users", {})
    
    if not users:
        await message.answer("📊 Пока нет игроков в таблице лидеров!")
        return
    
    # Сортируем по очкам (по убыванию)
    sorted_users = sorted(users.items(), key=lambda x: x[1], reverse=True)
    
    # Берём топ-10
    top_users = sorted_users[:10]
    
    leaderboard_text = "🏆 ТАБЛИЦА ЛИДЕРОВ 🏆\n\n"
    for i, (user_id, score) in enumerate(top_users, 1):
        # Пытаемся получить имя пользователя (если не получится - просто ID)
        try:
            user = await bot.get_chat(int(user_id))
            name = user.first_name or f"User_{user_id}"
        except:
            name = f"User_{user_id}"
        
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        leaderboard_text += f"{medal} {name} — {score} очков\n"
    
    await message.answer(leaderboard_text)

# --- Команда /reset (сброс счёта) ---

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

# --- Главная функция запуска ---

async def main():
    print("🤖 Бот запущен и готов к работе!")
    print(f"📁 Данные сохраняются в файл: {DATA_FILE}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
