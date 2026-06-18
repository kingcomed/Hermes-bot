import os
import json
import logging
import httpx
import redis
from fastapi import FastAPI, Request, Form
from fastapi.responses import PlainTextResponse
from groq import Groq
from twilio.rest import Client as TwilioClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# ===== ENVIRONMENT VARIABLES ZOTE =====
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
REDIS_URL = os.environ.get("REDIS_URL")

# WhatsApp Meta
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "hermes123")

# SMS - Twilio inafanya kazi na Voda
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN")
TWILIO_PHONE = os.environ.get("TWILIO_PHONE") # +255...

# Email - Tumia Gmail App Password
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")

# ===== UNGANISHA SERVICES =====
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("Redis connected")
except Exception as e:
    logger.error(f"Redis failed: {e}")
    redis_client = None

try:
    twilio_client = TwilioClient(TWILIO_SID, TWILIO_TOKEN) if TWILIO_SID else None
except:
    twilio_client = None

# ===== KUMBUKUMBU FUNCTIONS =====
def get_chat_history(user_id):
    if not redis_client: return []
    try:
        history = redis_client.get(f"chat:{user_id}")
        return json.loads(history) if history else []
    except: return []

def save_chat_history(user_id, history):
    if not redis_client: return
    try:
        redis_client.setex(f"chat:{user_id}", 604800, json.dumps(history[-20:]))
    except Exception as e:
        logger.error(f"Redis save error: {e}")

def get_groq_response(user_id, user_message, platform="unknown"):
    try:
        history = get_chat_history(user_id)
        history.append({"role": "user", "content": user_message})

        messages = [
            {
                "role": "system",
                "content": f"Wewe ni Hermes AI. Unajibu kupitia {platform}. Jibu Kiswahili fasaha, ufupi, kirafiki. Kumbuka mazungumzo ya nyuma. Kama ni SMS, jibu kifupi sana chini ya maneno 160."
            }
        ] + history[-10:]

        groq_client = Groq(api_key=GROQ_API_KEY)
        chat_completion = groq_client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant",
            temperature=0.8,
            max_tokens=600 if platform!= "sms" else 100,
        )

        reply = chat_completion.choices[0].message.content
        history.append({"role": "assistant", "content": reply})
        save_chat_history(user_id, history)
        return reply
    except Exception as e:
        logger.error(f"Groq Error: {e}")
        return "Samahani, nimechoka kidogo. Jaribu tena."

# ===== SEND FUNCTIONS KWA KILA PLATFORM =====
def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    with httpx.Client() as client:
        client.post(url, json={"chat_id": chat_id, "text": text})

def send_whatsapp(to_number, text):
    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }
    with httpx.Client() as client:
        client.post(url, headers=headers, json=data)

def send_sms(to_number, text):
    if twilio_client:
        twilio_client.messages.create(body=text, from_=TWILIO_PHONE, to=to_number)

# ===== ENDPOINTS ZOTE =====

@app.get("/")
def home():
    return {
        "status": "Hermes Multi-Platform Bot Live",
        "platforms": {
            "telegram": bool(TELEGRAM_TOKEN),
            "whatsapp": bool(WHATSAPP_TOKEN),
            "sms": bool(TWILIO_SID),
            "redis": redis_client is not None
        }
    }

# 1. TELEGRAM
@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id or not text: return {"ok": True}

    if text == "/start":
        send_telegram(chat_id, "Mambo! Mimi Hermes AI. Nina kumbukumbu kwenye Telegram, WhatsApp, SMS zote.")
        return {"ok": True}

    if text == "/sahau":
        redis_client.delete(f"chat:tg_{chat_id}")
        send_telegram(chat_id, "Nimesahau yote mkuu.")
        return {"ok": True}

    reply = get_groq_response(f"tg_{chat_id}", text, "Telegram")
    send_telegram(chat_id, reply)
    return {"ok": True}

# 2. WHATSAPP
@app.get("/whatsapp")
async def whatsapp_verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return int(challenge)
    return {"error": "Failed"}

@app.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    data = await request.json()
    try:
        entry = data["entry"][0]["changes"][0]["value"]
        if "messages" in entry:
            message = entry["messages"][0]
            from_number = message["from"]
            text = message["text"]["body"]

            reply = get_groq_response(f"wa_{from_number}", text, "WhatsApp")
            send_whatsapp(from_number, reply)
    except Exception as e:
        logger.error(f"WhatsApp error: {e}")
    return {"status": "received"}

# 3. SMS VODA - TWILIO
@app.post("/sms")
async def sms_webhook(From: str = Form(...), Body: str = Form(...)):
    reply = get_groq_response(f"sms_{From}", Body, "sms")
    send_sms(From, reply)
    return PlainTextResponse("")

# 4. EMAIL WEBHOOK - Tumia SendGrid Inbound Parse au Mailgun
@app.post("/email")
async def email_webhook(request: Request):
    data = await request.json()
    from_email = data.get("from")
    subject = data.get("subject", "")
    text = data.get("text", "")

    reply = get_groq_response(f"email_{from_email}", f"Subject: {subject}\n\n{text}", "Email")
    # Hapa unaweza kutumia SendGrid kutuma jibu
    logger.info(f"Email reply to {from_email}: {reply}")
    return {"status": "received"}
