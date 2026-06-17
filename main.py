from flask import Flask
import os
import threading
import time
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return "Hermes Bot iko Live ✅"

@app.route('/health')
def health():
    return "OK", 200

def ping_self():
    while True:
        try:
            url = os.environ.get('RENDER_EXTERNAL_URL')
            if url:
                requests.get(url + '/health')
                print("Self-ping: Hermes yuko hai")
        except Exception as e:
            print(f"Ping error: {e}")
        time.sleep(600)  # Ping kila dakika 10

if __name__ == '__main__':
    threading.Thread(target=ping_self, daemon=True).start()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
