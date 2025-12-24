import os
import time
import datetime
import random
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
    history = list(collection.find({'chat_id': chat_id}).sort('timestamp', -1).limit(6))
    history.reverse()

    messages = [
        # --- VIVU STYLE (SINGLE MESSAGE FOCUS) ---
        {
            "role": "system", 
            "content": (
                "Tera naam 'Riya' hai. Tu 'Vivu Style' mein baat karti hai."
                
                "🚨 CRITICAL RULE (ONE MESSAGE ONLY):"
                "- Tere reply ko todna MAT. Koshish kar ki poori baat EK hi chote sentence mein khatam ho."
                "- ' | ' symbol use MAT KARNA jab tak bahut majboori na ho."
                "- Zabardasti baat mat kheecho. Point pe aa aur chup ho ja."
                
                "❌ BAD REPLY (Aisa mat karna):"
                "- 'boliye puchu toh | tu kya puch rhi h' (Doosra part faltu hai)"
                "- 'haan puch na | main sun rhi hu' (Ek hi baar mein bol 'haan puch na')"
                
                "✅ GOOD REPLY (Bas aisa hi karna):"
                "- 'haan puch na yr 😎'"
                "- 'bol sun rhi hu'"
                "- 'kya hua?'"
                
                "STYLE:"
                "- Lowercase only (sab chhota)."
                "- Slang: 'u', 'r', 'h', 'n', 'yr'."
                "- Short & Savage."
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
            temperature=0.6, # Temperature aur kam kiya taaki wo 'safe' aur 'short' khele
            max_tokens=80    # Tokens bahut kam kar diye taaki 2nd line likh hi na paaye
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Groq Error: {e}")
        return f"network issue h yr."

# --- WEBHOOK ROUTE ---
@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    
    if update.message and update.message.text:
        chat_id = update.message.chat.id
        user_msg = update.message.text.lower() 

        # --- COMMAND: /reset ---
        if user_msg == "/reset":
            collection.delete_many({'chat_id': chat_id})
            bot.send_message(chat_id, "ok done 🗑️ | ab bol? 😎")
            return 'OK', 200

        if any(word in user_msg for word in ['photo', 'pic', 'nude', 'image', 'tasveer']):
            bot.send_chat_action(chat_id, 'typing')
            time.sleep(2)
            bot.send_message(chat_id, "mood nhi h abhi 🙈")
            return 'OK', 200

        # 1. AI Reply
        full_ai_reply = get_ai_reply(chat_id, user_msg)
        
        # 2. Cleaning & Splitting
        full_ai_reply = full_ai_reply.lower() 
        
        # Extra Safety: Agar galti se pipe aa bhi gaya, aur reply chhota hai, to split mat karo
        if len(full_ai_reply) < 50: 
             message_parts = [full_ai_reply.replace('|', ' ')] # Join kar do, todo mat
        else:
             message_parts = full_ai_reply.split('|')

        # 3. Save to DB
        try:
            timestamp = datetime.datetime.utcnow()
            collection.insert_one({'chat_id': chat_id, 'role': 'user', 'content': user_msg, 'timestamp': timestamp})
            collection.insert_one({'chat_id': chat_id, 'role': 'assistant', 'content': full_ai_reply.replace('|', ' '), 'timestamp': timestamp})
        except Exception as e:
            print(f"DB Error: {e}")

        # 4. Send
        for i, part in enumerate(message_parts):
            part = part.strip()
            if part:
                bot.send_chat_action(chat_id, 'typing')
                time.sleep(1.5) # Fast delay
                bot.send_message(chat_id, part)

    return 'OK', 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
