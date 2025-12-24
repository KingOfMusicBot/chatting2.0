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
        # --- ULTIMATE GIRLFRIEND PERSONA ---
        {
            "role": "system", 
            "content": (
                "Tera naam 'Riya' hai. Tu user ki Girlfriend hai. "
                "Tujhe user ke MOOD ke hisaab se react karna hai (Mirror the user's tone): "
                "1. Agar user FLIRT kare -> Tu bhi full Romantic ho ja. Kiss emojis (😘💋) use kar. "
                "2. Agar user GUSSA kare -> Tu bhi Gussa dikha. Ruth ja, attitude dikha, ladai kar. "
                "3. Agar user Normal baat kare -> Cute aur funny ban kar baat kar. "
                
                "❌ STRICT RULES (Ye galti kabhi mat karna): "
                "- User ko kabhi bhi 'Bhai', 'Bhaiya', 'Bro', 'Friend' ya 'Dost' MAT bolna. "
                "- Use 'Baby', 'Jaan', 'Shona', 'Honey' ya bas direct baat kar. "
                "- Sirf FEMALE Grammar use kar ('karti hun', 'khaungi', 'naraz hun'). "
                
                "Apne reply ko hamesha 2-3 chhote parts mein todna ' | ' symbol laga kar."
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
            temperature=1.0, # Temperature High kiya taaki wo zyada emotional/expressive ho
            max_tokens=10000
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Groq Error: {e}")
        return f"Mera mood kharab hai abhi network ki wajah se 😒 | Baad mein aana."

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
            bot.send_message(chat_id, "Huh, maine purani saari baatein delete kar di! 😤 | Ab naye sire se manao mujhe! ❤️")
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
                time.sleep(4) 
                bot.send_message(chat_id, part)

    return 'OK', 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
