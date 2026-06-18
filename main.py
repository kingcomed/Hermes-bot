from flask import Flask, request
import requests
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# --- ENVIRONMENT VARIABLES ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
WHATSAPP_TOKEN = os.environ.get('WHATSAPP_TOKEN')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'HERMES_VERIFY_TOKEN')
EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASS = os.environ.get('EMAIL_PASS')
VODA_NUMBER = os.environ.get('VODA_NUMBER')

@app.route("/")
def home():
    return "Hermes Bot iko Live ❤️ Telegram + WhatsApp + SMS"

@app.route("/health")
def health():
    return {"status": "ok"}

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

@app.route("/whatsapp", methods=['GET', 'POST'])
def whatsapp_webhook():
    if request.method == 'GET':
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
            reply = f"WhatsApp: Umesema '{text}'\n\nHermes Bot iko Live mkuu! 🚀"
            requests.post(
                f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages",
                headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "text": {"body": reply}
                }
            )
        except Exception as e:
            print(f"WhatsApp Error: {e}")
        return {"status": "ok"}, 200

@app.route("/sms", methods=['POST'])
def send_sms():
    data = request.get_json()
    message = data.get("message", "Hermes Bot Test")

    if not all([EMAIL_USER, EMAIL_PASS, VODA_NUMBER]):
        return {"error": "EMAIL_USER, EMAIL_PASS au VODA_NUMBER haijawekwa"}, 400

    voda_email = f"{VODA_NUMBER}@sms.vodacom.co.tz"
    msg = MIMEText(message)
    msg['Subject'] = ""
    msg['From'] = EMAIL_USER
    msg['To'] = voda_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
        return {"status": f"SMS imetumwa kwenda {VODA_NUMBER}"}
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run()
