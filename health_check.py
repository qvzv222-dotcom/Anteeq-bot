"""Health check server for UptimeBot monitoring - runs in separate process"""
import os
import sys
from flask import Flask, jsonify
import logging

logging.disable(logging.CRITICAL)

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for UptimeBot"""
    return jsonify({"status": "ok", "service": "telegram_bot"}), 200

@app.route('/', methods=['GET'])
def root():
    """Root endpoint for monitoring"""
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Error starting health check server: {e}", file=sys.stderr)
        sys.exit(1)
