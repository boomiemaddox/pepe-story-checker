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
VERIFY_STORY_URL = "https://peparioserver-xcy5.onrender.com/api/telegram/verify-story?id={user_id}"
ADD_STORY_URL = "https://peparioserver-xcy5.onrender.com/api/telegram/add-story"

app = FastAPI()

@app.get("/api/verify_stories")
async def verify_stories():
    async with TelegramClient("session", API_ID, API_HASH) as client:
        users = fetch_users_to_verify()

        for user in users:
            username = user.get("username")
            user_id = user.get("id")

            if not username or not user_id:
                continue

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
                verify_user_story(user_id)
                print(f"✅ @{username} ({user_id}) верифицирован!")

    return {"success": True, "message": "Все пользователи проверены"}

def fetch_users_to_verify():
    headers = {"X-Auth-Key": X_AUTH_KEY}
    response = requests.get(FETCH_USERS_URL, headers=headers)
    
    if response.status_code == 200:
        return response.json()
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
    return "https://i.imgur.com/mWzitST.jpeg"

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

def verify_user_story(user_id):
    headers = {"X-Auth-Key": X_AUTH_KEY}
    response = requests.head(VERIFY_STORY_URL.format(user_id=user_id), headers=headers)
    
    if response.status_code == 200:
        print(f"✅ История для ID {user_id} подтверждена!")
        return True
    else:
        print(f"❌ Ошибка подтверждения истории ID {user_id}")
        return False

