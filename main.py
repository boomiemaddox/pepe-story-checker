import asyncio
import requests
from fastapi import FastAPI
from telethon import TelegramClient
from telethon.tl.functions.stories import GetPeerStoriesRequest
from skimage.metrics import structural_similarity as ssim
import cv2
import numpy as np
from PIL import Image
import io
import os
from dotenv import load_dotenv

load_dotenv()  # ✅ Загружаем переменные окружения


# вставьте нужные данные пожалуйста, спасибо
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
FETCH_USERS_URL = "https://peparioserver-xcy5.onrender.com/api/telegram/users-stories"
VERIFY_STORY_URL = "https://peparioserver-xcy5.onrender.com/api/telegram/verify-story?username={username}"

# === СОЗДАЕМ СЕРВИС ===
app = FastAPI()

@app.get("/api/verify_stories")
async def verify_stories():
    async with TelegramClient("session", API_ID, API_HASH) as client:
        users = await fetch_users_to_verify()

        for username in users:
            latest_story = await get_latest_story(client, username)
            if latest_story is None:
                continue

            expected_image_url = get_initial_story_image(username)
            if expected_image_url is None:
                continue

            expected_image = download_image(expected_image_url)
            if expected_image is None:
                continue

            if compare_images(latest_story, expected_image):
                requests.head(VERIFY_STORY_URL.format(username=username))
                print(f"✅ @{username} верифицирован")

    return {"success": True, "message": "Все юзеры проверены"}

async def fetch_users_to_verify():
    try:
        response = requests.get(FETCH_USERS_URL)
        return response.json() if response.status_code == 200 else []
    except:
        return []

async def get_latest_story(client, username):
    try:
        entity = await client.get_entity(username)
        stories = await client(GetPeerStoriesRequest(peer=entity))
        if stories.stories:
            media = stories.stories[-1].media
            buffer = await client.download_media(media, bytes)
            return Image.open(io.BytesIO(buffer))
    except:
        return None

def get_initial_story_image(username):
    # тут нужно будет получать URL загруженного изображения (первоначальная сторис)
    return None

def download_image(url):
    try:
        response = requests.get(url)
        return Image.open(io.BytesIO(response.content)) if response.status_code == 200 else None
    except:
        return None

def compare_images(img1, img2, threshold=0.6):
    img1 = cv2.cvtColor(np.array(img1), cv2.COLOR_RGB2GRAY)
    img2 = cv2.cvtColor(np.array(img2), cv2.COLOR_RGB2GRAY)
    img1 = cv2.resize(img1, (img2.shape[1], img2.shape[0])) 
    similarity, _ = ssim(img1, img2, full=True)
    return similarity >= threshold
