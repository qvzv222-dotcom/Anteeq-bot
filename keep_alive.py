from flask import Flask
from threading import Thread
import time
import requests

app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Функция для самопинга
def ping_self():
    while True:
        try:
            requests.get("https://ANTEEQ-BOT.qvzv222.repl.co")
        except:
            pass
        time.sleep(300)  # Пинг каждые 5 минут

keep_alive()
