import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("8875824495:AAGcaII9dC54zhTvfgbxCsgj7JIizZpThjc")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    # Railway дает порт через переменную PORT
    port = int(os.getenv("PORT", 8080))
    
    # Запускаем веб-хук для Railway
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=f"https://{os.getenv('RAILWAY_STATIC_URL')}/webhook"
    )

if __name__ == "__main__":
    main()
