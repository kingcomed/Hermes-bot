from flask import Flask, request
import requests
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# --- ENVIRONMENT VARIABLES ZOTE ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
WHATSAPP_TOKEN = os.environ.get('WHATSAPP_TOKEN')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'HERMES_VERIFY_TOKEN') # Default
EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASS = os.environ.get('EMAIL_PASS')
VODA_NUMBER = os.environ.get('VODA_NUMBER')
# ZINGINE ZA BAADAE - USIJALI
OPENAI_KEY = os.environ.get('OPENAI_KEY')
DATABASE_URL = os.environ.get('DATABASE_URL')

# --- HOME & HEALTH ---
@app.route("/")
def home():
    return "Hermes Bot iko Live ❤️ Telegram + WhatsApp + SMS + Future"

@app.route("/health")
def health():
    return {"status": "ok", "services": ["telegram", "whatsapp", "sms"]}

# --- 1. TELEGRAM BOT ---
@app.route("/telegram", methods=['POST'])
def telegram_webhook():
    if not TELEGRAM_TOKEN:
        return {"error": "TELEGRAM_TOKEN haijawekwa"}, 400

    data = request.get_json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        reply = f"Telegram: Umesema '{text}'\n\nHermes Bot iko Live mkuu! 🚀"
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply}
        )
    return {"ok": True}

# --- 2. WHATSAPP BOT ---
@app.route("/whatsapp", methods=['GET', 'POST'])
def whatsapp_webhook():
    if request.method == 'GET':
        # Meta Verification
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        return "Verification failed", 403

    if request.method == 'POST':
        if not all([WHATSAPP_TOKEN, PHONE_NUMBER_ID]):
            return {"error": "WHATSAPP_TOKEN au PHONE_NUMBER_ID haijawekwa"}, 400

        data = request.get_json()
        try:
            phone = data['entry'][0]['changes'][0]['value']['messages'][0]['from']
            text = data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
