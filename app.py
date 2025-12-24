import os
import time
import datetime
from flask import Flask, request
import telebot
from pymongo import MongoClient
from groq import Groq

# --- CONFIGURATION (Heroku Env Vars se ayega) ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# --- SETUP ---
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# MongoDB Connection
try:
    client = MongoClient(MONGO_URI)
    db = client.get_database('telegram_bot')
    collection = db.chats
except Exception as e:
    print(f"MongoDB Error: {e}")

# Groq Client
client_groq = Groq(api_key=GROQ_API_KEY)

# --- AI LOGIC ---
def get_ai_reply(chat_id, user_msg):
    # 1. Fetch History (Last 10 messages)
    history = list(collection.find({'chat_id': chat_id}).sort('timestamp', -1).limit(10))
    history.reverse() # Purane message pehle, naye baad mein

    messages = [
        # System Prompt: Bot ka behavior set karein
        {"role": "system", "content": "Tumhara naam 'Rocky' hai. Tum ek smart aur funny dost ho. Tum Hinglish (Hindi+English mix) mein baat karte ho. Short aur natural reply dena."}
    ]

    # History add karein
    for msg in history:
        messages.append({"role": msg['role'], "content": msg['content']})

    # Naya message add karein
    messages.append({"role": "user", "content": user_msg})

    try:
        # Groq API Call
        completion = client_groq.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.7,
            max_tokens=200
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Sorry yaar, server down hai abhi. ({str(e)})"

# --- FLASK ROUTES ---

# Home Route (To keep bot alive)
@app.route('/')
def home():
    return "Bot is running on Python! 🐍"

# Webhook Route (Telegram yahan message bhejega)
@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    
    # Update process karein
    if update.message and update.message.text:
        chat_id = update.message.chat.id
        user_msg = update.message.text

        # 1. Typing Action dikhayein
        bot.send_chat_action(chat_id, 'typing')

        # 2. AI se reply lein
        ai_reply = get_ai_reply(chat_id, user_msg)

        # 3. Database mein save karein
        try:
            timestamp = datetime.datetime.utcnow()
            collection.insert_one({'chat_id': chat_id, 'role': 'user', 'content': user_msg, 'timestamp': timestamp})
            collection.insert_one({'chat_id': chat_id, 'role': 'assistant', 'content': ai_reply, 'timestamp': timestamp})
        except Exception as e:
            print(f"DB Save Error: {e}")

        # 4. Message Send Karein
        bot.send_message(chat_id, ai_reply)

    return 'OK', 200

# --- RUN SERVER ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
