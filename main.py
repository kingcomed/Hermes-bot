import os
import requests
import smtplib
from email.mime.text import MIMEText
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse

app = FastAPI()

# TOKENS ZOTE
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# 1. FUNCTION YA AI - INATUMIKA KILA MAHALI
def ask_ai(user_message: str, platform: str = "telegram"):
    """AI moja kwa app zote"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

    system_msg = {
        "telegram": "Wewe ni Hermes Bot wa Telegram. Jibu kwa Kiswahili cha mtaani, mcheshi na mfupi.",
        "whatsapp": "Wewe ni Hermes Bot wa WhatsApp. Jibu kwa Kiswahili rasmi kidogo, mfupi na wazi.",
        "email": "Wewe ni Hermes AI. Jibu barua kwa Kiswahili fasaha na kitaalamu.",
        "api": "Jibu moja kwa moja bila salamu."
    }

    data = {
        "model": "llama-3.1-70b-versatile",
        "messages": [
            {"role": "system", "content": system_msg.get(platform, system_msg["api"])},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7,
        "max_tokens": 300
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        return response.json()["choices"][0]["message"]["content"]
    except:
        return "Samahani, nimechoka kidogo. Jaribu tena baadae."

# 2. SEND FUNCTIONS - KILA PLATFORM
def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def send_whatsapp(to_number, text):
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "text": {"body": text}
    }
    requests.post(url, headers=headers, json=data)

def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = to_email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)

# 3. HOME ROUTE
@app.get("/")
def home():
    return {"status": "Hermes Bot: Telegram + WhatsApp + Email + API Live"}

# 4. TELEGRAM WEBHOOK
@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"].get("text", "")

        if user_text == "/start":
            reply = "Mambo mkuu! Mimi ni Hermes AI 🚀 Niulize chochote."
        else:
            reply = ask_ai(user_text, "telegram")

        send_telegram(chat_id, reply)
    return {"ok": True}

# 5. WHATSAPP WEBHOOK
@app.get("/whatsapp")
async def whatsapp_verify(request: Request):
    """Meta inatumia hii ku-verify webhook"""
    if request.query_params.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(request.query_params.get("hub.challenge"))
    raise HTTPException(status_code=403, detail="Token mbaya")

@app.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    data = await request.json()
    try:
        entry = data["entry"][0]["changes"][0]["value"]
        if "messages" in entry:
            msg = entry["messages"][0]
            from_number = msg["from"]
            user_text = msg["text"]["body"]

            reply = ask_ai(user_text, "whatsapp")
            send_whatsapp(from_number, reply)
    except:
        pass
    return {"ok": True}

# 6. EMAIL ENDPOINT - TUMA EMAIL KWA API
@app.post("/send-email")
async def api_send_email(request: Request):
    data = await request.json()
    to = data.get("to")
    subject = data.get("subject")
    prompt = data.get("prompt") # AI atatunga body

    if not all([to, subject, prompt]):
        raise HTTPException(status_code=400, detail="Hakikisha 'to', 'subject', 'prompt' zipo")

    body = ask_ai(prompt, "email")
    send_email(to, subject, body)
    return {"status": f"Email imetumwa kwa {to}"}

# 7. GENERIC API - KWA APP YOYOTE
@app.post("/api/ask")
async def generic_api(request: Request):
    data = await request.json()
    question = data.get("question", "")
    reply = ask_ai(question, "api")
    return {"question": question, "answer": reply}
