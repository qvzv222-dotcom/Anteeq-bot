from flask import Flask, jsonify
import threading
import time

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "Bot is running"}), 200

def run_server():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def start_health_check():
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(2)  # Give server time to start

if __name__ == '__main__':
    run_server()
