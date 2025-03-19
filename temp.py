import os
from telethon.sync import TelegramClient
api_id = 16070558
api_hash = 'e04e7b75b4c3e73ec091f66e68a32d17'

client = TelegramClient("pepe_story_checker", api_id, api_hash)
client.start()
