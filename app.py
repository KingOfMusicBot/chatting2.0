import os
import time
import datetime
from flask import Flask, request
import telebot
from pymongo import MongoClient
from groq import Groq

# --- CONFIGURATION ---
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
    # History fetch karo
    history = list(collection.find({'chat_id': chat_id}).sort('timestamp', -1).limit(8))
    history.reverse()

    messages = [
        # --- NAME CHANGED TO RIYA ---
        {
            "role": "system", 
            "content": (
                "Tera naam 'Riya' hai. Tu user ki Girlfriend hai."
                "IMPORTANT: Tere replies BAHUT SHORT aur NATURAL hone chahiye. (Max 5-8 words per part)."
                "Lambe paragraphs bilkul mat likhna. Real chatting style copy kar. "
                
                "MOOD RULES:"
                "1. Flirt: Short & Cute. Example: 'Aww baby 😘', 'Sach mein? 🙈', 'Love you!'"
                "2. Gussa: One word replies. Example: 'Hmm', 'Mat kar baat', 'Bye', 'Huh 😒'."
                "3. Normal: Seedha jawab de. Example: 'Haan kha liya', 'Tu bata?'"
                
                "STRICT RULES:"
                "- No 'Bhai/Bhaiya'. "
                "- Only Female Grammar ('karti hun', 'gayi thi')."
                "- Reply ko ' | ' se todna lekin har part chhota rakhna."
            )
        }
    ]

    for msg in history:
        messages.append({"role": msg['role'], "content": msg['content']})

    messages.append({"role": "user", "content": user_msg})

    try:
        completion = client_groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Groq Error: {e}")
        return f"Network issue hai 😒 | Baad mein baat karte hain."

# --- WEBHOOK ROUTE ---
@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    
    if update.message and update.message.text:
        chat_id = update.message.chat.id
        user_msg = update.message.text

        # --- COMMAND: /reset ---
        if user_msg == "/reset":
            collection.delete_many({'chat_id': chat_id})
            bot.send_message(chat_id, "Theek hai, ab main Riya hun! ❤️ | Nayi shuruwat karte hain!")
            return 'OK', 200

        # 1. AI Reply
        full_ai_reply = get_ai_reply(chat_id, user_msg)
        
        # 2. Split Messages
        message_parts = full_ai_reply.split('|')

        # 3. Save to DB
        try:
            timestamp = datetime.datetime.utcnow()
            collection.insert_one({'chat_id': chat_id, 'role': 'user', 'content': user_msg, 'timestamp': timestamp})
            collection.insert_one({'chat_id': chat_id, 'role': 'assistant', 'content': full_ai_reply.replace('|', ' '), 'timestamp': timestamp})
        except Exception as e:
            print(f"DB Error: {e}")

        # 4. Send with Delay
        for part in message_parts:
            part = part.strip()
            if part:
                bot.send_chat_action(chat_id, 'typing')
                time.sleep(3)
                bot.send_message(chat_id, part)

    return 'OK', 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
