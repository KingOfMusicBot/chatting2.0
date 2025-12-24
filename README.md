# 🐍 Smart AI Telegram Bot (Python Version)

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Framework-Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![Groq](https://img.shields.io/badge/AI-Groq_Llama3-f55036?style=for-the-badge)
![MongoDB](https://img.shields.io/badge/Database-MongoDB_Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)

A high-speed, human-like Telegram Chatbot built with **Python (Flask)**. It utilizes **Groq API (Llama 3)** for instant AI responses and **MongoDB** to maintain conversation memory.

> **Why Python?** Unlike PHP, this version runs persistently, handles threading better, and has zero dependency-locking issues on Heroku.

---

## 🚀 Features

* **⚡ Blazing Fast:** Uses Groq's LPU inference engine for instant replies.
* **🧠 Smart Memory:** Remembers the last 10 messages for context-aware conversations.
* **💬 Human-Like:** Shows "Typing..." status while generating responses.
* **🐍 Python Power:** Built on Flask & pyTelegramBotAPI for stability.
* **☁️ 100% Free Hosting:** Compatible with Heroku (Eco/Basic) and Render.

---

## 🛠️ Prerequisites

1.  **Telegram Bot Token:** From [@BotFather](https://t.me/BotFather).
2.  **Groq API Key:** From [Groq Cloud Console](https://console.groq.com/).
3.  **MongoDB URI:** From [MongoDB Atlas](https://www.mongodb.com/atlas).
    * *Note:* Whitelist IP `0.0.0.0/0` in MongoDB Network Access.

---

## 🚀 Deployment

### Option 1: One-Click Deploy (Easiest)

Deploy straight to Heroku with a single click.

<a href="https://heroku.com/deploy?template=https://github.com/YOUR_USERNAME/YOUR_REPO_NAME">
  <img src="https://www.herokucdn.com/deploy/button.svg" alt="Deploy">
</a>

> **Important:** Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` in the link above with your actual GitHub repository details.

### Option 2: Manual Deployment (CLI)

```bash
# Clone the repo
git clone [https://github.com/your-username/your-repo.git](https://github.com/your-username/your-repo.git)
cd your-repo

# Login & Create App
heroku login
heroku create your-app-name

# Set Config Vars
heroku config:set TELEGRAM_TOKEN="your_token"
heroku config:set GROQ_API_KEY="your_key"
heroku config:set MONGO_URI="mongodb+srv://..."

# Deploy
git push heroku master
