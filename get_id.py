import requests
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('TELEGRAM_BOT_TOKEN')

print(f"Checking for messages sent to bot: {token[:10]}...")
url = f"https://api.telegram.org/bot{token}/getUpdates"
response = requests.get(url).json()

if response.get("result"):
    for update in response["result"]:
        chat_id = update["message"]["chat"]["id"]
        first_name = update["message"]["chat"]["first_name"]
        print(f"SUCCESS! Found Chat ID for {first_name}: {chat_id}")
else:
    print("No messages found. ACTION REQUIRED: Open your bot in Telegram and send it a message saying 'Hello' right now, then run this script again.")
