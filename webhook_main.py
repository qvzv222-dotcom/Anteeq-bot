
import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import webhook_db as db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger('httpx').setLevel(logging.WARNING)

# Конфигурация
BOT_TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')  # https://your-app.onrender.com

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL не найден в переменных окружения")

# Flask приложение для webhook
app = Flask(__name__)

# Telegram Application
application = Application.builder().token(BOT_TOKEN).build()

# Здесь добавляются все handlers из test_main.py
# (Копируем все функции-обработчики и setup_handlers)

@app.route('/')
def health_check():
    return 'Bot is running!', 200

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
async def webhook():
    """Обработка webhook от Telegram"""
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, application.bot)
    await application.process_update(update)
    return 'OK', 200

async def setup_webhook():
    """Установка webhook"""
    webhook_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
    await application.bot.set_webhook(webhook_url)
    print(f"✅ Webhook установлен: {webhook_url}")

if __name__ == '__main__':
    # Инициализация БД
    db.init_db()
    
    # Настройка handlers
    # setup_handlers(application)  # Добавьте все handlers сюда
    
    # Установка webhook
    import asyncio
    asyncio.run(setup_webhook())
    
    # Запуск Flask сервера
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
