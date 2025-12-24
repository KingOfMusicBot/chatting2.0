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
    history = list(collection.find({'chat_id': chat_id}).sort('timestamp', -1).limit(10))
    history.reverse()

    messages = [
        # SYSTEM PROMPT: Yahan hum bot ko batayenge ki wo ek ladki hai
        {
            "role": "system", 
            "content": (
                "Tumhara naam 'Riya' hai. Tum ek cute, bubbly aur friendly ladki ho. "
                "Tum Hinglish (Hindi+English) mein baat karti ho aur dher saare emojis use karti ho. "
                "IMPORTANT: Apne reply ko hamesha 2 ya 3 chhote parts mein todna. "
                "Har part ke beech mein ' | ' (pipe symbol) lagana taaki main unhe alag messages mein bhej sakun. "
                "Example: 'Haan baba samajh gayi 🙈 | Main abhi thoda busy hoon | Baad mein baat karein? ❤️'"
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
            temperature=0.8, # Thoda creative banaya
            max_tokens=10000
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Oof sorry baba, network issue hai 🥺 "

# --- WEBHOOK ROUTE ---
@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    
    if update.message and update.message.text:
        chat_id = update.message.chat.id
        user_msg = update.message.text

        # 1. Pehle AI se reply lo
        full_ai_reply = get_ai_reply(chat_id, user_msg)
        
        # 2. Reply ko '|' se tod kar alag-alag messages banao
        message_parts = full_ai_reply.split('|')

        # 3. Database mein user ka message save karo
        try:
            timestamp = datetime.datetime.utcnow()
            collection.insert_one({'chat_id': chat_id, 'role': 'user', 'content': user_msg, 'timestamp': timestamp})
            # Bot ka full reply bhi save kar lete hain future context ke liye
            collection.insert_one({'chat_id': chat_id, 'role': 'assistant', 'content': full_ai_reply.replace('|', ' '), 'timestamp': timestamp})
        except Exception as e:
            print(f"DB Error: {e}")

        # 4. Loop chala kar messages bhejo (Delay ke saath)
        for part in message_parts:
            part = part.strip() # Extra spaces hatao
            if part:
                # Typing action dikhao (Human feel ke liye)
                bot.send_chat_action(chat_id, 'typing')
                
                # 5-6 second ka delay (jaisa aapne kaha)
                time.sleep(5) 
                
                bot.send_message(chat_id, part)

    return 'OK', 200

# --- RUN SERVER ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
