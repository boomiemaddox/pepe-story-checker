import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
X_AUTH_KEY = "3730a1cfc7b4bb32645b38bf32ace833e1592eb9a686872c4ed78de2a0e8dc0d"

FETCH_USERS_URL = "https://peparioserver-xcy5.onrender.com/api/telegram/users-stories"
VERIFY_STORY_URL = "https://peparioserver-xcy5.onrender.com/api/telegram/verify-story?username={username}"

app = FastAPI()

@app.get("/api/verify_stories")
async def verify_stories():
    logger.info(f"📡 verify stirues")

    async with TelegramClient("session", API_ID, API_HASH) as client:
        usernames = fetch_users_to_verify()
        print(f"👥 Полученные юзеры: {usernames}")

        verified_users = []

        for username in usernames:
            print(f"🔍 Проверяем @{username}")

            latest_story = await get_latest_story(client, username)
            if latest_story is None:
                print(f"❌ У @{username} нет сторис!")
                continue

            expected_image_url = get_initial_story_image(username)
            if expected_image_url is None:
                print(f"❌ Не нашли эталонное изображение для @{username}!")
                continue

            expected_image = download_image(expected_image_url)
            if expected_image is None:
                print(f"❌ Не смогли скачать эталонное изображение для @{username}!")
                continue

            if compare_images(latest_story, expected_image):
                verify_user_story(username)
                verified_users.append(username)
                print(f"✅ @{username} верифицирован!")

    return {"success": True, "verified_users": verified_users}



def fetch_users_to_verify():
    headers = {"X-Auth-Key": X_AUTH_KEY}
    response = requests.get(FETCH_USERS_URL, headers=headers)

    if response.status_code == 200:
        users = response.json()
        
        if not users:  # Если сервер вернул пустой список
            print("⚠️ Сервер вернул пустой список, используем тестовый.")
            return ["boomiemaddox", "toronto_ls", "pepario"]  # 🔹 Временные тестовые юзеры
        
        return users  # Если сервер дал юзеров — используем их
    
    print("❌ Ошибка получения списка пользователей с сервера")
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
    return "https://i.imgur.com/HcUg3Bm.jpeg"

def download_image(url):
    try:
        print(f"🔽 Загружаем изображение: {url}")
        response = requests.get(url)
        if response.status_code == 200:
            print("✅ Успешно скачали!")
            return Image.open(io.BytesIO(response.content))
        else:
            print("❌ Ошибка загрузки изображения!")
            return None
    except Exception as e:
        print(f"❌ Ошибка при скачивании: {e}")
        return None


def compare_images(img1, img2, threshold=0.6):
    img1 = cv2.cvtColor(np.array(img1), cv2.COLOR_RGB2GRAY)
    img2 = cv2.cvtColor(np.array(img2), cv2.COLOR_RGB2GRAY)
    img1 = cv2.resize(img1, (img2.shape[1], img2.shape[0])) 
    
    similarity, _ = ssim(img1, img2, full=True)
    logger.info(f"📊 Коэффициент схожести: {similarity:.2f}")

    return similarity >= threshold



def verify_user_story(username):
    headers = {"X-Auth-Key": X_AUTH_KEY}
    response = requests.head(VERIFY_STORY_URL.format(username=username), headers=headers)
    
    if response.status_code == 200:
        print(f"✅ История для @{username} подтверждена!")
        return True
    else:
        print(f"❌ Ошибка подтверждения истории @{username}")
        return False
