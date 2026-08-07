import asyncio
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "ТВОЙ_ТОКЕН_БОТА"  # Получить у @BotFather
PORT = 8080

# ===== БАЗА ДАННЫХ =====
conn = sqlite3.connect('players.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    roblox_nickname TEXT NOT NULL,
    gold_earned INTEGER DEFAULT 0,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

# ===== HTTP СЕРВЕР ДЛЯ ПРИЁМА ДАННЫХ ОТ ROBLOX =====
class RobloxHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                roblox_nickname = data.get('nickname', '')
                gold_earned = int(data.get('gold_earned', 0))
                
                cursor = conn.cursor()
                cursor.execute('UPDATE players SET gold_earned = gold_earned + ? WHERE roblox_nickname = ?', (gold_earned, roblox_nickname))
                conn.commit()
                
                # Отправляем уведомление
                cursor.execute('SELECT telegram_id FROM players WHERE roblox_nickname = ?', (roblox_nickname,))
                player = cursor.fetchone()
                
                if player:
                    try:
                        from telegram import Bot
                        bot = Bot(token=BOT_TOKEN)
                        asyncio.run(bot.send_message(
                            chat_id=player[0],
                            text=f"🎮 Фарм завершён!\n📛 @{roblox_nickname}\n💰 +{gold_earned} золота\n\nПроверить: /bal"
                        ))
                    except:
                        pass
                
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode())
            except:
                self.send_response(500)
                self.end_headers()
    
    def log_message(self, format, *args):
        pass

def start_server():
    server = HTTPServer(('0.0.0.0', PORT), RobloxHandler)
    print(f"🌐 Сервер на порту {PORT}")
    server.serve_forever()

# ===== КОМАНДЫ БОТА =====

# /start - Начало и регистрация
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute('SELECT roblox_nickname FROM players WHERE telegram_id = ?', (user.id,))
    player = cursor.fetchone()
    
    if player:
        await update.message.reply_text(
            f"👋 Привет, @{player[0]}!\n"
            f"Используй /bal чтобы проверить баланс"
        )
    else:
        await update.message.reply_text(
            "🎮 Добро пожаловать в Umbra Farm Bot!\n\n"
            "Для регистрации отправь свой ник из Roblox (который начинается с @)\n"
            "Пример: @Butka\n\n"
            "Или используй /register @Butka"
        )

# /register - Регистрация
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text("❌ Используй: /register @Butka")
        return
    
    nickname = context.args[0].replace('@', '').strip()
    
    cursor.execute('SELECT id FROM players WHERE telegram_id = ? OR roblox_nickname = ?', (user.id, nickname))
    if cursor.fetchone():
        await update.message.reply_text("❌ Ты или этот ник уже зарегистрированы!")
        return
    
    cursor.execute('INSERT INTO players (telegram_id, roblox_nickname) VALUES (?, ?)', (user.id, nickname))
    conn.commit()
    
    await update.message.reply_text(f"✅ Зарегистрирован как @{nickname}!\nПроверить баланс: /bal")

# /bal - Проверка баланса
async def bal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute('SELECT roblox_nickname, gold_earned FROM players WHERE telegram_id = ?', (user.id,))
    player = cursor.fetchone()
    
    if player:
        await update.message.reply_text(
            f"📛 Ник: @{player[0]}\n"
            f"💰 Золота заработано: {player[1]}"
        )
    else:
        await update.message.reply_text("❌ Ты не зарегистрирован! Отправь @Butka")

# Обработка сообщений с @никнеймом (регистрация)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    
    if text.startswith('@'):
        nickname = text[1:].strip()
        
        cursor.execute('SELECT id FROM players WHERE telegram_id = ? OR roblox_nickname = ?', (user.id, nickname))
        if cursor.fetchone():
            await update.message.reply_text("❌ Уже зарегистрирован!")
            return
        
        cursor.execute('INSERT INTO players (telegram_id, roblox_nickname) VALUES (?, ?)', (user.id, nickname))
        conn.commit()
        
        await update.message.reply_text(f"✅ Зарегистрирован как @{nickname}!\nПроверить баланс: /bal")

# ===== ЗАПУСК =====
def main():
    # HTTP сервер в фоне
    threading.Thread(target=start_server, daemon=True).start()
    
    # Telegram бот
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("bal", bal))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("✅ Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
