import os

from telethon.sync import TelegramClient
api_id = os.getenv("API_ID")  # Replace with your API_ID
api_hash = os.getenv("API_HASH")  # Replace with your API_HASH

client = TelegramClient("session", api_id, api_hash)
client.start()
