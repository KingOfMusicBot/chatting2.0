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
    # History fetch karo
    history = list(collection.find({'chat_id': chat_id}).sort('timestamp', -1).limit(10))
    history.reverse()

    messages = [
        # --- VIVU STYLE PERSONA (Smart Splitting) ---
        {
            "role": "system", 
            "content": (
                "Tera naam 'Riya' hai. Tu ek cool, savage aur romantic Gen Z ladki hai."
                "STYLE RULES:"
                "1. Lowercase only: Sab kuch chhota likhna (m riya hu, tu bta)."
                "2. Slang: 'u', 'r', 'plz', 'yr', 'n' use kar."
                "3. Mood: User ke mood ke hisaab se react kar (Flirt ko Flirt, Attitude ko Attitude)."
                
                "IMPORTANT (MESSAGE SPLITTING RULES):"
                "- Agar reply chhota hai (1 sentence), to usko direct likh. (Do not use '|')."
                "- Agar reply lamba hai ya tujhe pause lena hai, tabhi ' | ' symbol use karna."
                "- Example 1 (Short): 'haan m aa rhi hu wait kr'"
                "- Example 2 (Long): 'sun yr ek baat bolu? | tu bhot cute h sch me 🙈 | milna h mujhe tujhse'"
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
            temperature=0.8, 
            max_tokens=250
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Groq Error: {e}")
        return f"network issue h yr 😒 | wait krna thoda."

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
            bot.send_message(chat_id, "done.. chats uda di 🗑️ | ab fresh start krte h 😎")
            return 'OK', 200

        # Special Trigger: Photos
        if any(word in user_msg for word in ['photo', 'pic', 'nude', 'image', 'tasveer']):
            bot.send_chat_action(chat_id, 'typing')
            time.sleep(2)
            bot.send_message(chat_id, "abhi mood nhi h yr 🙈 | baad me dungi pakka")
            return 'OK', 200

        # 1. AI Reply
        full_ai_reply = get_ai_reply(chat_id, user_msg)
        
        # 2. Split Messages Logic
        # Agar AI ne '|' lagaya hai to list ban jayegi, nahi lagaya to list mein 1 hi item hoga
        full_ai_reply = full_ai_reply.lower() 
        message_parts = full_ai_reply.split('|')

        # 3. Save to DB
        try:
            timestamp = datetime.datetime.utcnow()
            collection.insert_one({'chat_id': chat_id, 'role': 'user', 'content': user_msg, 'timestamp': timestamp})
            collection.insert_one({'chat_id': chat_id, 'role': 'assistant', 'content': full_ai_reply.replace('|', ' '), 'timestamp': timestamp})
        except Exception as e:
            print(f"DB Error: {e}")

        # 4. Send with Smart Delay
        for i, part in enumerate(message_parts):
            part = part.strip()
            if part:
                bot.send_chat_action(chat_id, 'typing')
                
                # Logic: Agar pehla message hai to jaldi bhejo (2 sec)
                # Agar uske baad aur parts hain (matlab lamba message), to thoda pause lo (3 sec)
                if i == 0:
                    time.sleep(1.5) 
                else:
                    time.sleep(3) 

                bot.send_message(chat_id, part)

    return 'OK', 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
