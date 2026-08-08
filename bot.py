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

# Словарь для хранения состояния ожидания ставки
waiting_for_bet = {}

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

# --- Обработчик ставок для казино ---

@dp.message()
async def handle_bet(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем, ждём ли мы ставку от этого пользователя
    if user_id not in waiting_for_bet:
        return
    
    # Получаем данные о ставке
    bet_data = waiting_for_bet[user_id]
    menu_message_id = bet_data["menu_message_id"]
    
    try:
        # Пытаемся преобразовать текст в число
        bet = int(message.text.strip())
        
        # Проверяем, что ставка положительная
        if bet <= 0:
            await message.reply("❌ Ставка должна быть больше 0!")
            return
        
        # Проверяем, хватает ли очков
        current_score = get_user_score(user_id)
        if bet > current_score:
            await message.reply(f"❌ У тебя только {current_score} очков! Сделай ставку меньше.")
            return
        
        # Удаляем пользователя из ожидания
        del waiting_for_bet[user_id]
        
        # Запускаем игру в казино со ставкой
        await play_casino(message, user_id, bet, menu_message_id)
        
    except ValueError:
        await message.reply("❌ Введи число! Например: 10")

# --- Функция игры в казино ---

async def play_casino(message: types.Message, user_id: int, bet: int, menu_message_id: int):
    # Отправляем анимированный слот
    slot_message = await message.answer_dice(emoji="🎰")
    value = slot_message.dice.value
    
    # Ждём окончания анимации
    await asyncio.sleep(3.5)
    
    points = 0
    multiplier = 0
    result_text = ""
    chat_result = ""
    
    # Логика казино
    if value == 6:  # 777 (джекпот)
        multiplier = 3
        points = bet * multiplier
        result_text = f"🎰 ДЖЕКПОТ! 777!\n💰 Ставка: {bet} x{multiplier} = +{points} очков!"
        chat_result = f"🎰 ДЖЕКПОТ! Ты выиграл {points} очков (ставка {bet} x{multiplier})!"
    elif value == 5:  # Три одинаковых
        multiplier = 1.5
        points = int(bet * multiplier)
        result_text = f"🎰 Три одинаковых! {value}{value}{value}\n💰 Ставка: {bet} x{multiplier} = +{points} очков!"
        chat_result = f"🎰 Три одинаковых! Ты выиграл {points} очков (ставка {bet} x{multiplier})!"
    elif value == 4:  # Три одинаковых
        multiplier = 1.5
        points = int(bet * multiplier)
        result_text = f"🎰 Три одинаковых! {value}{value}{value}\n💰 Ставка: {bet} x{multiplier} = +{points} очков!"
        chat_result = f"🎰 Три одинаковых! Ты выиграл {points} очков (ставка {bet} x{multiplier})!"
    else:
        result_text = f"🎰 Выпало: {value}\n😕 Ты проиграл {bet} очков!"
        chat_result = f"🎰 Выпало: {value}\n😕 Ты проиграл {bet} очков!"
        points = -bet
    
    # Обновляем счёт
    update_user_score(user_id, points)
    new_score = get_user_score(user_id)
    
    # Кнопки "Ещё раз?" и "Выбрать другое" ПРЯМО ПОД ЭМОДЗИ
    keyboard = [
        [InlineKeyboardButton(text="🎰 Ещё раз?", callback_data="casino_again")],
        [InlineKeyboardButton(text="📋 Выбрать другое", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Отправляем результат в чат
    await message.answer(f"{chat_result}\n💰 Твой счёт: {new_score} очков.")
    
    # Редактируем исходное меню с кнопками ПОД ЭМОДЗИ
    try:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=menu_message_id,
            text=f"🎰 КАЗИНО 🎰\n\n{result_text}\n\n💰 Твой счёт: {new_score} очков.",
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Ошибка редактирования: {e}")

# --- Обработчик игр (КНОПКИ) ---

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    game = callback.data
    
    # --- Обработка кнопки "Выбрать другое" ---
    if game == "main_menu":
        await callback.answer()
        score = get_user_score(user_id)
        keyboard = [
            [InlineKeyboardButton(text="🎲 Кости", callback_data="dice")],
            [InlineKeyboardButton(text="🎰 Казино", callback_data="casino")],
            [InlineKeyboardButton(text="🏀 Баскетбол", callback_data="basketball")],
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback.message.edit_text(
            text=f"🎮 Главное меню\n\n💰 Твой счёт: {score} очков.\n\nВыбери игру:",
            reply_markup=reply_markup
        )
        return
    
    # --- Обработка кнопки "Ещё раз?" для казино ---
    if game == "casino_again":
        # Проверяем КД
        now = datetime.now()
        if user_id in cooldown:
            time_diff = (now - cooldown[user_id]).total_seconds()
            if time_diff < 4:
                remaining = 4 - time_diff
                await callback.answer(f"⏳ Подожди {remaining:.1f} сек!", show_alert=False)
                return
        
        cooldown[user_id] = now
        current_score = get_user_score(user_id)
        
        if current_score <= 0:
            await callback.answer("❌ У тебя 0 очков! Сыграй в другие игры.", show_alert=True)
            return
        
        # Сохраняем ID сообщения
        waiting_for_bet[user_id] = {
            "menu_message_id": callback.message.message_id
        }
        
        await callback.answer()
        
        cancel_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_bet")]
            ]
        )
        
        await callback.message.edit_text(
            text=f"🎰 КАЗИНО 🎰\n\n"
                 f"💰 Твой счёт: {current_score} очков.\n"
                 f"📝 Напиши количество очков, которое хочешь поставить.\n\n"
                 f"💡 Правила:\n"
                 f"• 777 (6) → x3\n"
                 f"• Три одинаковых (4-5) → x1.5\n"
                 f"• Остальное → проигрыш\n\n"
                 f"✏️ Введи число в чат:",
            reply_markup=cancel_keyboard
        )
        return
    
    # --- Обработка кнопки "Ещё раз?" для костей ---
    if game == "dice_again":
        # Проверяем КД
        now = datetime.now()
        if user_id in cooldown:
            time_diff = (now - cooldown[user_id]).total_seconds()
            if time_diff < 4:
                remaining = 4 - time_diff
                await callback.answer(f"⏳ Подожди {remaining:.1f} сек!", show_alert=False)
                return
        
        cooldown[user_id] = now
        # Запускаем игру в кости
        await play_dice(callback, user_id)
        return
    
    # --- Обработка кнопки "Ещё раз?" для баскетбола ---
    if game == "basketball_again":
        # Проверяем КД
        now = datetime.now()
        if user_id in cooldown:
            time_diff = (now - cooldown[user_id]).total_seconds()
            if time_diff < 4:
                remaining = 4 - time_diff
                await callback.answer(f"⏳ Подожди {remaining:.1f} сек!", show_alert=False)
                return
        
        cooldown[user_id] = now
        # Запускаем игру в баскетбол
        await play_basketball(callback, user_id)
        return
    
    # --- ОТМЕНА СТАВКИ ---
    if game == "cancel_bet":
        if user_id in waiting_for_bet:
            del waiting_for_bet[user_id]
        
        await callback.answer("❌ Ставка отменена")
        
        # Возвращаем главное меню
        keyboard = [
            [InlineKeyboardButton(text="🎲 Кости", callback_data="dice")],
            [InlineKeyboardButton(text="🎰 Казино", callback_data="casino")],
            [InlineKeyboardButton(text="🏀 Баскетбол", callback_data="basketball")],
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            text=f"🎮 Главное меню\n\n💰 Твой счёт: {get_user_score(user_id)} очков.\n\nВыбери игру:",
            reply_markup=reply_markup
        )
        return
    
    # --- Проверка КД для основных игр (4 секунды) ---
    now = datetime.now()
    if user_id in cooldown:
        time_diff = (now - cooldown[user_id]).total_seconds()
        if time_diff < 4:
            remaining = 4 - time_diff
            await callback.answer(f"⏳ Подожди {remaining:.1f} сек!", show_alert=False)
            return
    
    cooldown[user_id] = now
    
    print(f"🔔 Нажата кнопка: {game} от пользователя {user_id}")
    
    # --- ИГРА В КОСТИ ---
    if game == "dice":
        await play_dice(callback, user_id)
    
    # --- ИГРА В КАЗИНО ---
    elif game == "casino":
        current_score = get_user_score(user_id)
        if current_score <= 0:
            await callback.answer("❌ У тебя 0 очков! Сыграй в другие игры.", show_alert=True)
            return
        
        waiting_for_bet[user_id] = {
            "menu_message_id": callback.message.message_id
        }
        
        await callback.answer()
        
        cancel_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_bet")]
            ]
        )
        
        await callback.message.edit_text(
            text=f"🎰 КАЗИНО 🎰\n\n"
                 f"💰 Твой счёт: {current_score} очков.\n"
                 f"📝 Напиши количество очков, которое хочешь поставить.\n\n"
                 f"💡 Правила:\n"
                 f"• 777 (6) → x3\n"
                 f"• Три одинаковых (4-5) → x1.5\n"
                 f"• Остальное → проигрыш\n\n"
                 f"✏️ Введи число в чат:",
            reply_markup=cancel_keyboard
        )
    
    # --- ИГРА В БАСКЕТБОЛ ---
    elif game == "basketball":
        await play_basketball(callback, user_id)

# --- Функция игры в кости ---

async def play_dice(callback: types.CallbackQuery, user_id: int):
    # Отправляем анимированный кубик
    dice_message = await callback.message.answer_dice(emoji="🎲")
    value = dice_message.dice.value
    
    await asyncio.sleep(3.5)
    
    dice_emoji = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    current_score = get_user_score(user_id)
    points = 0
    
    if value == 6:
        points = 2
        result_text = f"🎲 Выпало: {dice_emoji[value]} ({value})\n🎉 Поздравляю! Ты выиграл 2 очка!"
        chat_result = f"🎲 Выпало: {dice_emoji[value]} ({value})\n🎉 Ты выиграл 2 очка!"
    else:
        result_text = f"🎲 Выпало: {dice_emoji[value]} ({value})\n😕 Попробуй ещё раз!"
        chat_result = f"🎲 Выпало: {dice_emoji[value]} ({value})\n😕 Ты ничего не выиграл!"
    
    if points > 0:
        update_user_score(user_id, points)
        new_score = get_user_score(user_id)
    else:
        new_score = current_score
    
    # Кнопки ПРЯМО ПОД ЭМОДЗИ
    keyboard = [
        [InlineKeyboardButton(text="🎲 Ещё раз?", callback_data="dice_again")],
        [InlineKeyboardButton(text="📋 Выбрать другое", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Отправляем в чат
    await callback.message.answer(f"{chat_result}\n💰 Твой счёт: {new_score} очков.")
    
    # Обновляем меню
    await callback.answer()
    await callback.message.edit_text(
        text=f"🎲 КОСТИ 🎲\n\n{result_text}\n\n💰 Твой счёт: {new_score} очков.",
        reply_markup=reply_markup
    )

# --- Функция игры в баскетбол ---

async def play_basketball(callback: types.CallbackQuery, user_id: int):
    # Отправляем анимированный баскетбол
    basket_message = await callback.message.answer_dice(emoji="🏀")
    value = basket_message.dice.value
    
    await asyncio.sleep(3.5)
    
    current_score = get_user_score(user_id)
    points = 0
    
    if value >= 4:
        points = 2
        result_text = "🏀🏆 Ты попал в корзину! +2 очка!"
        chat_result = "🏀🏆 Ты попал в корзину! +2 очка!"
    else:
        result_text = "🏀❌ Промах! Попробуй ещё раз."
        chat_result = "🏀❌ Промах! Ты ничего не выиграл!"
    
    if points > 0:
        update_user_score(user_id, points)
        new_score = get_user_score(user_id)
    else:
        new_score = current_score
    
    # Кнопки ПРЯМО ПОД ЭМОДЗИ
    keyboard = [
        [InlineKeyboardButton(text="🏀 Ещё раз?", callback_data="basketball_again")],
        [InlineKeyboardButton(text="📋 Выбрать другое", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Отправляем в чат
    await callback.message.answer(f"{chat_result}\n💰 Твой счёт: {new_score} очков.")
    
    # Обновляем меню
    await callback.answer()
    await callback.message.edit_text(
        text=f"🏀 БАСКЕТБОЛ 🏀\n\n{result_text}\n\n💰 Твой счёт: {new_score} очков.",
        reply_markup=reply_markup
    )

# --- ЗАПУСК ---

async def main():
    print("🤖 Бот запущен на Railway с ПОЛЛИНГОМ!")
    print("📁 Данные сохраняются в:", DATA_FILE)
    print("🔄 Начинаем polling...")
    print("⏳ КД между нажатиями: 4 секунды")
    print("🎰 Казино работает со ставками (x3 за 777, x1.5 за три одинаковых)")
    print("✅ /start НЕ сбрасывает очки")
    print("✅ Кнопки 'Ещё раз?' и 'Выбрать другое' работают!")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
