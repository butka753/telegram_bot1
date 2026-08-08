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

# --- Настройки КД ---
COOLDOWN_DICE = 4       # Кости - 4 секунды
COOLDOWN_CASINO = 4     # Казино - 4 секунды
COOLDOWN_BASKETBALL = 10 # Баскетбол - 10 секунд

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

# --- Функция проверки КД ---

def check_cooldown(user_id: int, game_type: str) -> tuple:
    """Проверяет КД для игры. Возвращает (можно_играть, оставшиеся_секунды)"""
    now = datetime.now()
    
    if user_id not in cooldown:
        return True, 0
    
    # Получаем время последнего нажатия для этой игры
    last_time = cooldown[user_id].get(game_type, datetime.min)
    time_diff = (now - last_time).total_seconds()
    
    # Выбираем КД в зависимости от игры
    if game_type == "dice":
        cooldown_time = COOLDOWN_DICE
    elif game_type == "casino":
        cooldown_time = COOLDOWN_CASINO
    elif game_type == "basketball":
        cooldown_time = COOLDOWN_BASKETBALL
    else:
        cooldown_time = 4
    
    if time_diff < cooldown_time:
        remaining = cooldown_time - time_diff
        return False, remaining
    
    return True, 0

def update_cooldown(user_id: int, game_type: str):
    """Обновляет время последнего нажатия для игры"""
    if user_id not in cooldown:
        cooldown[user_id] = {}
    cooldown[user_id][game_type] = datetime.now()

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
    
    if user_id not in waiting_for_bet:
        return
    
    bet_data = waiting_for_bet[user_id]
    menu_message_id = bet_data["menu_message_id"]
    
    try:
        bet = int(message.text.strip())
        
        if bet <= 0:
            await message.reply("❌ Ставка должна быть больше 0!")
            return
        
        current_score = get_user_score(user_id)
        if bet > current_score:
            await message.reply(f"❌ У тебя только {current_score} очков!")
            return
        
        del waiting_for_bet[user_id]
        await play_casino(message, user_id, bet, menu_message_id)
        
    except ValueError:
        await message.reply("❌ Введи число! Например: 10")

# --- Функция игры в казино ---

async def play_casino(message: types.Message, user_id: int, bet: int, menu_message_id: int):
    slot_message = await message.answer_dice(emoji="🎰")
    value = slot_message.dice.value
    
    await asyncio.sleep(3.5)
    
    points = 0
    multiplier = 0
    result_text = ""
    
    # Логика казино с 7-кой
    if value == 6:  # 777 (джекпот)
        multiplier = 3
        points = bet * multiplier
        result_text = f"🎰 ДЖЕКПОТ! 777!\n💰 Ставка: {bet} x{multiplier} = +{points} очков!"
    elif value == 5:  # Три одинаковых (555)
        multiplier = 1.5
        points = int(bet * multiplier)
        result_text = f"🎰 Три одинаковых! {value}{value}{value}\n💰 Ставка: {bet} x{multiplier} = +{points} очков!"
    elif value == 4:  # Три одинаковых (444)
        multiplier = 1.5
        points = int(bet * multiplier)
        result_text = f"🎰 Три одинаковых! {value}{value}{value}\n💰 Ставка: {bet} x{multiplier} = +{points} очков!"
    elif value == 7:  # Если вдруг выпала 7 (но в dice значения только 1-6)
        # На всякий случай, если телеграм изменит логику
        multiplier = 0.3
        points = int(bet * multiplier)
        result_text = f"🎰 Выпала 7!\n💰 Возврат: {bet} x{multiplier} = +{points} очков!"
    else:
        # Проверяем, есть ли хоть одна 7 в значении (для эмуляции)
        # В телеграм dice для казино выдаёт значения 1-6, поэтому 7 эмулируем через value == 1
        if value == 1:  # Эмулируем выпадение 7 (утешительный приз)
            multiplier = 0.3
            points = int(bet * multiplier)
            result_text = f"🎰 Выпало: {value} (повезло!)\n💰 Возврат: {bet} x{multiplier} = +{points} очков!"
        else:
            result_text = f"🎰 Выпало: {value}\n😕 Ты проиграл {bet} очков!"
            points = -bet
    
    update_user_score(user_id, points)
    new_score = get_user_score(user_id)
    
    # КНОПКИ ПОД ЭМОДЗИ В ЧАТЕ
    keyboard = [
        [InlineKeyboardButton(text="🎰 Ещё раз?", callback_data="casino_again")],
        [InlineKeyboardButton(text="📋 Выбрать другое", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Отправляем результат с кнопками ПОД ЭМОДЗИ
    await message.answer(
        f"{result_text}\n💰 Твой счёт: {new_score} очков.",
        reply_markup=reply_markup
    )
    
    # Обновляем меню (без кнопок, просто текст)
    try:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=menu_message_id,
            text=f"🎰 КАЗИНО 🎰\n\nИгра окончена!\n💰 Твой счёт: {new_score} очков."
        )
    except Exception as e:
        print(f"Ошибка: {e}")

# --- Обработчик игр ---

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    game = callback.data
    
    # --- КНОПКА "ВЫБРАТЬ ДРУГОЕ" ---
    if game == "main_menu":
        await callback.answer()
        score = get_user_score(user_id)
        
        keyboard = [
            [InlineKeyboardButton(text="🎲 Кости", callback_data="dice")],
            [InlineKeyboardButton(text="🎰 Казино", callback_data="casino")],
            [InlineKeyboardButton(text="🏀 Баскетбол", callback_data="basketball")],
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.answer(
            f"🎮 Привет, {callback.from_user.first_name}!\n"
            f"💰 Твой счёт: {score} очков.\n\n"
            f"Выбери игру:",
            reply_markup=reply_markup
        )
        
        await callback.message.delete()
        return
    
    # --- КНОПКА "ЕЩЁ РАЗ?" ДЛЯ КАЗИНО ---
    if game == "casino_again":
        # Проверяем КД для казино
        can_play, remaining = check_cooldown(user_id, "casino")
        if not can_play:
            await callback.answer(f"⏳ Подожди {remaining:.1f} сек!", show_alert=False)
            return
        
        update_cooldown(user_id, "casino")
        
        current_score = get_user_score(user_id)
        
        if current_score <= 0:
            await callback.answer("❌ У тебя 0 очков!", show_alert=True)
            return
        
        await callback.message.delete()
        
        waiting_for_bet[user_id] = {
            "menu_message_id": callback.message.message_id
        }
        
        await callback.answer()
        
        cancel_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_bet")]
            ]
        )
        
        await callback.message.answer(
            f"🎰 КАЗИНО 🎰\n\n"
            f"💰 Твой счёт: {current_score} очков.\n"
            f"📝 Напиши количество очков для ставки.\n\n"
            f"💡 Правила:\n"
            f"• 777 (6) → x3\n"
            f"• Три одинаковых (4-5) → x1.5\n"
            f"• 7 (1) → возврат x0.3\n"
            f"• Остальное → проигрыш\n\n"
            f"✏️ Введи число в чат:",
            reply_markup=cancel_keyboard
        )
        return
    
    # --- КНОПКА "ЕЩЁ РАЗ?" ДЛЯ КОСТЕЙ ---
    if game == "dice_again":
        # Проверяем КД для костей
        can_play, remaining = check_cooldown(user_id, "dice")
        if not can_play:
            await callback.answer(f"⏳ Подожди {remaining:.1f} сек!", show_alert=False)
            return
        
        update_cooldown(user_id, "dice")
        
        await callback.message.delete()
        await play_dice(callback, user_id)
        return
    
    # --- КНОПКА "ЕЩЁ РАЗ?" ДЛЯ БАСКЕТБОЛА ---
    if game == "basketball_again":
        # Проверяем КД для баскетбола (10 секунд)
        can_play, remaining = check_cooldown(user_id, "basketball")
        if not can_play:
            await callback.answer(f"⏳ Подожди {remaining:.1f} сек!", show_alert=False)
            return
        
        update_cooldown(user_id, "basketball")
        
        await callback.message.delete()
        await play_basketball(callback, user_id)
        return
    
    # --- ОТМЕНА СТАВКИ ---
    if game == "cancel_bet":
        if user_id in waiting_for_bet:
            del waiting_for_bet[user_id]
        
        await callback.answer("❌ Ставка отменена")
        await callback.message.delete()
        return
    
    # --- ОСНОВНЫЕ ИГРЫ ИЗ МЕНЮ ---
    
    # Определяем тип игры для КД
    if game == "dice":
        game_type = "dice"
        cooldown_time = COOLDOWN_DICE
    elif game == "casino":
        game_type = "casino"
        cooldown_time = COOLDOWN_CASINO
    elif game == "basketball":
        game_type = "basketball"
        cooldown_time = COOLDOWN_BASKETBALL
    else:
        game_type = "unknown"
        cooldown_time = 4
    
    # Проверяем КД
    can_play, remaining = check_cooldown(user_id, game_type)
    if not can_play:
        await callback.answer(f"⏳ Подожди {remaining:.1f} сек!", show_alert=False)
        return
    
    update_cooldown(user_id, game_type)
    
    print(f"🔔 Нажата кнопка: {game} от {user_id}")
    
    # --- ИГРА В КОСТИ ---
    if game == "dice":
        await play_dice(callback, user_id)
    
    # --- ИГРА В КАЗИНО ---
    elif game == "casino":
        current_score = get_user_score(user_id)
        if current_score <= 0:
            await callback.answer("❌ У тебя 0 очков!", show_alert=True)
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
                 f"📝 Напиши количество очков для ставки.\n\n"
                 f"💡 Правила:\n"
                 f"• 777 (6) → x3\n"
                 f"• Три одинаковых (4-5) → x1.5\n"
                 f"• 7 (1) → возврат x0.3\n"
                 f"• Остальное → проигрыш\n\n"
                 f"✏️ Введи число в чат:",
            reply_markup=cancel_keyboard
        )
    
    # --- ИГРА В БАСКЕТБОЛ ---
    elif game == "basketball":
        await play_basketball(callback, user_id)

# --- Функция игры в кости ---

async def play_dice(callback: types.CallbackQuery, user_id: int):
    dice_message = await callback.message.answer_dice(emoji="🎲")
    value = dice_message.dice.value
    
    await asyncio.sleep(3.5)
    
    dice_emoji = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    current_score = get_user_score(user_id)
    points = 0
    
    if value == 6:
        points = 2
        result_text = f"🎲 Выпало: {dice_emoji[value]} ({value})\n🎉 Ты выиграл 2 очка!"
    else:
        result_text = f"🎲 Выпало: {dice_emoji[value]} ({value})\n😕 Ты ничего не выиграл!"
    
    if points > 0:
        update_user_score(user_id, points)
        new_score = get_user_score(user_id)
    else:
        new_score = current_score
    
    # КНОПКИ ПОД ЭМОДЗИ
    keyboard = [
        [InlineKeyboardButton(text="🎲 Ещё раз?", callback_data="dice_again")],
        [InlineKeyboardButton(text="📋 Выбрать другое", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.answer()
    
    # Отправляем результат с кнопками
    await callback.message.answer(
        f"{result_text}\n💰 Твой счёт: {new_score} очков.",
        reply_markup=reply_markup
    )
    
    # Обновляем меню (просто текст без кнопок)
    try:
        await callback.message.edit_text(
            text=f"🎲 КОСТИ 🎲\n\nИгра окончена!\n💰 Твой счёт: {new_score} очков."
        )
    except Exception as e:
        print(f"Ошибка: {e}")

# --- Функция игры в баскетбол ---

async def play_basketball(callback: types.CallbackQuery, user_id: int):
    basket_message = await callback.message.answer_dice(emoji="🏀")
    value = basket_message.dice.value
    
    await asyncio.sleep(3.5)
    
    current_score = get_user_score(user_id)
    points = 0
    
    if value >= 4:
        points = 2
        result_text = "🏀🏆 Ты попал в корзину! +2 очка!"
    else:
        result_text = "🏀❌ Промах! Ты ничего не выиграл!"
    
    if points > 0:
        update_user_score(user_id, points)
        new_score = get_user_score(user_id)
    else:
        new_score = current_score
    
    # КНОПКИ ПОД ЭМОДЗИ
    keyboard = [
        [InlineKeyboardButton(text="🏀 Ещё раз?", callback_data="basketball_again")],
        [InlineKeyboardButton(text="📋 Выбрать другое", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.answer()
    
    # Отправляем результат с кнопками
    await callback.message.answer(
        f"{result_text}\n💰 Твой счёт: {new_score} очков.",
        reply_markup=reply_markup
    )
    
    # Обновляем меню (просто текст без кнопок)
    try:
        await callback.message.edit_text(
            text=f"🏀 БАСКЕТБОЛ 🏀\n\nИгра окончена!\n💰 Твой счёт: {new_score} очков."
        )
    except Exception as e:
        print(f"Ошибка: {e}")

# --- ЗАПУСК ---

async def main():
    print("🤖 Бот запущен!")
    print("📁 Данные в:", DATA_FILE)
    print("⏳ КД:")
    print(f"   🎲 Кости - {COOLDOWN_DICE} секунд")
    print(f"   🎰 Казино - {COOLDOWN_CASINO} секунд")
    print(f"   🏀 Баскетбол - {COOLDOWN_BASKETBALL} секунд")
    print("🎰 Казино: 777 (6) → x3, Три одинаковых (4-5) → x1.5, 7 (1) → возврат x0.3")
    print("✅ Кнопки ПОД ЭМОДЗИ в чате")
    print("✅ Кнопка 'Выбрать другое' открывает меню как /start")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
