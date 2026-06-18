import os
import logging
import httpx
from fastapi import FastAPI, Request
from groq import Groq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# USIWEKE client hapa nje - ndio inasababisha crash

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        with httpx.Client() as client:
            response = client.post(url, json=payload, timeout=30)
            response.raise_for_status()
        logger.info(f"Telegram sent: {chat_id}")
    except Exception as e:
        logger.error(f"Telegram send error: {e}")

def get_groq_response(user_message):
    try:
        # Tengeneza client hapa ndani ili avoid startup crash
        groq_client = Groq(api_key=GROQ_API_KEY)

        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Wewe ni Hermes AI, msaidizi mjanja kutoka Tanzania. Jibu kwa Kiswahili fasaha na ufupi."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
            max_tokens=500,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API Error: {e}")
        return "Samahani mkuu, AI imechoka. Jaribu tena."

@app.get("/")
def home():
    return {"status": "Hermes Bot Live"}

@app.post("/telegram")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"Telegram data: {data}")

        message = data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        if not chat_id or not text:
            return {"ok": True}

        if text == "/start":
            reply = "Mambo mkuu! Mimi ni Hermes AI 🚀 Niulize chochote."
            send_telegram_message(chat_id, reply)
            return {"ok": True}

        ai_reply = get_groq_response(text)
        send_telegram_message(chat_id, ai_reply)
        return {"ok": True}

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": True}
