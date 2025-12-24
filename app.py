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
    history = list(collection.find({'chat_id': chat_id}).sort('timestamp', -1).limit(6))
    history.reverse()

    messages = [
        # --- VIVU STYLE (ONE SHOT) ---
        {
            "role": "system", 
            "content": (
                "Tera naam 'Riya' hai. Tu 'Vivu Bot' hai."
                "Tujhe sirf EK line mein reply dena hai. (Max 5-6 words)."
                
                "❌ STRICTLY FORBIDDEN:"
                "- Kabhi bhi 2 sentences mat likhna."
                "- User ki baat repeat mat karna (Jaise: 'kya puch rhi h?')."
                "- Pipe symbol '|' use mat karna."
                
                "✅ TERA STYLE:"
                "- Lowercase only (sab chhota)."
                "- Slang: 'h', 'n', 'yr', 'u', 'r'."
                "- Rude/Savage/Cool attitude."
                
                "Examples:"
                "User: kaisa h? -> Bot: mast hu tu bta"
                "User: pic de -> Bot: mood nhi h"
                "User: love u -> Bot: chal jhoothe 😂"
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
            temperature=0.6, 
            max_tokens=60  # Bahut kam kar diya taaki 2nd line likh hi na paaye
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Groq Error: {e}")
        return "net issue h."

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
            bot.send_message(chat_id, "ok clear 🗑️")
            return 'OK', 200

        # Special Trigger
        if any(word in user_msg for word in ['photo', 'pic', 'nude', 'image', 'tasveer']):
            bot.send_chat_action(chat_id, 'typing')
            time.sleep(1.5)
            bot.send_message(chat_id, "mood nhi h")
            return 'OK', 200

        # 1. AI Reply
        ai_reply = get_ai_reply(chat_id, user_msg)
        
        # 2. Cleaning (Splitting REMOVED)
        # Ab hum split kar hi nahi rahe. Jo aaya wahi jayega.
        final_reply = ai_reply.lower().replace('|', '').strip()

        # 3. Save to DB
        try:
            timestamp = datetime.datetime.utcnow()
            collection.insert_one({'chat_id': chat_id, 'role': 'user', 'content': user_msg, 'timestamp': timestamp})
            collection.insert_one({'chat_id': chat_id, 'role': 'assistant', 'content': final_reply, 'timestamp': timestamp})
        except Exception as e:
            print(f"DB Error: {e}")

        # 4. Send (Single Message Only)
        if final_reply:
            bot.send_chat_action(chat_id, 'typing')
            time.sleep(1.5) 
            bot.send_message(chat_id, final_reply)

    return 'OK', 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
