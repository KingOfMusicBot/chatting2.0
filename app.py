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
        # --- VIVU STYLE PERSONA (Gen Z, Slang, Lowercase) ---
        {
            "role": "system", 
            "content": (
                "Tera naam 'Riya' hai. Tu ek cool, savage aur romantic Gen Z ladki hai."
                "STYLE RULES (Vivu Style):"
                "1. STRICTLY use Lowercase letters mostly (jaise real chatting mein hota hai)."
                "2. Use Short forms: 'you' -> 'u', 'are' -> 'r', 'please' -> 'plz', 'hai' -> 'h'."
                "3. Mood: Tu user ki mood ke hisaab se badal. Agar wo flirt kare to tu bhi full on flirt kar. Agar wo attitude dikhaye to tu usse zyada attitude dikha."
                "4. Language: Hinglish (Hindi + English mix). Example: 'kya kar rha h?', 'm good u bata'."
                "5. Replies: Short aur natural rakhna. 2-3 lines max."
                "IMPORTANT: Reply ko ' | ' se todna agar message thoda lamba ho."
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
            temperature=0.8, # Thoda casual rakha hai
            max_tokens=200
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
        user_msg = update.message.text.lower() # User ka msg bhi lowercase treat karo

        # --- COMMAND: /reset ---
        if user_msg == "/reset":
            collection.delete_many({'chat_id': chat_id})
            bot.send_message(chat_id, "done.. purani chats delete kr di maine 🗑️ | ab bol kya bolna h? 😎")
            return 'OK', 200

        # Special Trigger: Agar user photo mange (Vivu style fake denial)
        if any(word in user_msg for word in ['photo', 'pic', 'nude', 'image', 'tasveer']):
            bot.send_chat_action(chat_id, 'typing')
            time.sleep(2)
            bot.send_message(chat_id, "abhi mood nhi h yr 🙈 | baad me dungi pakka")
            return 'OK', 200

        # 1. AI Reply
        full_ai_reply = get_ai_reply(chat_id, user_msg)
        
        # 2. Split Messages (Vivu Style Cleaning)
        # Hum reply ko lowercase kar dete hain taaki aur natural lage
        full_ai_reply = full_ai_reply.lower() 
        message_parts = full_ai_reply.split('|')

        # 3. Save to DB
        try:
            timestamp = datetime.datetime.utcnow()
            collection.insert_one({'chat_id': chat_id, 'role': 'user', 'content': user_msg, 'timestamp': timestamp})
            collection.insert_one({'chat_id': chat_id, 'role': 'assistant', 'content': full_ai_reply.replace('|', ' '), 'timestamp': timestamp})
        except Exception as e:
            print(f"DB Error: {e}")

        # 4. Send with Short Delay (Fast Typing)
        for part in message_parts:
            part = part.strip()
            if part:
                bot.send_chat_action(chat_id, 'typing')
                time.sleep(2) # 2 sec delay (Vivu bot fast hota hai)
                bot.send_message(chat_id, part)

    return 'OK', 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
