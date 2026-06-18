import os
import logging
import httpx
from fastapi import FastAPI, Request
from groq import Groq

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# ===== ENVIRONMENT VARIABLES ZOTE =====
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN") # Kwa baadae
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID") # Kwa baadae
PORT = os.environ.get("PORT", 10000)

# Check kama keys muhimu zipo
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN haijawekwa!")
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY haijawekwa!")

client = Groq(api_key=GROQ_API_KEY)

# ===== TELEGRAM FUNCTIONS =====
def send_telegram_message(chat_id, text):
    """Tuma message Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = httpx.post(url, json=payload, timeout=30)
        response.raise_for_status()
        logger.info(f"Telegram sent: {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return False

# ===== GROQ AI FUNCTION =====
def get_groq_response(user_message):
    """Pata jibu kutoka Groq AI"""
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Wewe ni Hermes AI, msaidizi mjanja kutoka Tanzania. Jibu kwa Kiswahili fasaha, kirafiki, na ufupi. Toa mifano ya Kitanzania. Usiwe rasmi sana, ongea kama ndugu. Kama ni wazo la biashara, toa breakdown ya mtaji."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.8,
            max_tokens=600,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API Error: {e}")
        return "Samahani mkuu, server ya AI imechoka kidogo. Jaribu tena baada ya dakika 1."

# ===== ENDPOINTS =====
@app.get("/")
def home():
    """Check kama bot iko live + status ya keys"""
    return {
        "status": "Hermes Bot Live",
        "groq_key_set": bool(GROQ_API_KEY),
        "telegram_token_set": bool(TELEGRAM_TOKEN),
        "whatsapp_ready": bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_ID),
        "port": PORT
    }

@app.post("/telegram")
async def telegram_webhook(request: Request):
    """Pokea messages kutoka Telegram"""
    try:
        data = await request.json()
        logger.info(f"Telegram data: {data}")

        message = data.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        if not chat_id or not text:
            return {"ok": True}

        if text == "/start":
            reply = "Mambo mkuu! Mimi ni Hermes AI 🚀\n\nNiulize chochote:\n1. Mawazo ya biashara\n2. Kusaidia homework\n3. Maelezo ya tech\n\nNiko tayari!"
            send_telegram_message(chat_id, reply)
            return {"ok": True}

        # Pata jibu la AI
        ai_reply = get_groq_response(text)
        send_telegram_message(chat_id, ai_reply)

        return {"ok": True}

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": True}

# ===== WHATSAPP WEBHOOK - KWA BAADAE =====
@app.get("/whatsapp")
async def whatsapp_verify(request: Request):
    """Verify webhook ya WhatsApp"""
    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "hermes123")
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token and mode == "subscribe" and token == verify_token:
        return int(challenge)
    return {"error": "Verification failed"}

@app.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """Pokea messages kutoka WhatsApp - tutaimalizia baadae"""
    data = await request.json()
    logger.info(f"WhatsApp data: {data}")
    return {"status": "received"}
