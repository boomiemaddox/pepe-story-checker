import logging
import requests
import asyncio
import io
import base64
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from telethon import TelegramClient
from telethon.tl.functions.stories import GetPeerStoriesRequest
from telethon.tl.types import MessageMediaPhoto
from skimage.metrics import structural_similarity as ssim
import cv2
import numpy as np
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

session_data = os.getenv("SESSION_STRING")
if session_data:
    with open("pepe_story_checker.session", "wb") as session_file:
        session_file.write(base64.b64decode(session_data))

# Environment variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
X_AUTH_KEY = os.getenv("X_AUTH_KEY")
FETCH_USERS_URL = 'https://peparioserverdev.onrender.com/api/telegram/users-stories'
VERIFY_STORY_URL = 'https://peparioserverdev.onrender.com/api/telegram/verify-story?username={username}'

# Initialize FastAPI
app = FastAPI()

# Global cache for storing verified users
verified_users_cache = []

@app.get("/")
def read_root():
    return {"message": "Pepe Story Checker is running!"}

@app.get("/api/verified_users")
def get_verified_users():
    return {"verified_users": verified_users_cache}

@app.get("/api/verify_stories")
async def verify_stories():
    logger.info("🔍 Verifying stories...")

    async with TelegramClient("pepe_story_checker.session", API_ID, API_HASH) as client:
        logger.info("✅ Telegram client connected successfully.")
        usernames = await fetch_users_to_verify()
        logger.info(f"🧑‍🤝‍🧑 Users to verify: {usernames}")

        for username in usernames:
            logger.info(f"🔎 Checking @{username}")

            # Fetch the latest story
            latest_story = await get_latest_story(client, username)
            if latest_story is None:
                logger.warning(f"⚠️ @{username} has no stories!")
                continue

            # Get the reference image and compare
            expected_image_url = get_initial_story_image(username)
            if not expected_image_url:
                logger.warning(f"⚠️ No reference image found for @{username}!")
                continue

            expected_image = download_image(expected_image_url)
            if not expected_image:
                logger.warning(f"⚠️ Failed to download reference image for @{username}!")
                continue

            # Compare images and verify user story
            similarity_score, is_similar = compare_images(latest_story, expected_image)
            if is_similar:
                success = verify_user_story(username, similarity_score)
                if success:
                    verified_users_cache.append(username)
                    logger.info(f"✅ @{username} verified successfully!")

    return {"success": True, "verified_users": verified_users_cache}

async def fetch_users_to_verify():
    headers = {"X-Auth-Key": X_AUTH_KEY}
    logger.info(f"🔑 Sending request to fetch users with X-Auth-Key: {X_AUTH_KEY}")
    
    # Asynchronous request using asyncio
    response = await asyncio.to_thread(requests.get, FETCH_USERS_URL, headers=headers)
    logger.info(f"📩 Response Status Code: {response.status_code}")
    logger.info(f"📄 Response Content: {response.text}")

    if response.status_code == 200:
        users = response.json()
        logger.info(f"✅ Users fetched: {users}")
        return users

    logger.error(f"❌ Error fetching users: {response.status_code} - {response.text}")
    return []


async def get_latest_story(client, username):
    try:
        logger.info(f"📸 Fetching latest story for @{username}")
        entity = await client.get_entity(username)
        response = await client(GetPeerStoriesRequest(peer=entity))
        logger.info(f"📝 Raw Stories Response for @{username}: {response}")

        if response.stories.stories:
            latest_story = response.stories.stories[-1]
            media = latest_story.media

            if isinstance(media, MessageMediaPhoto) and hasattr(media, "photo"):
                buffer = await client.download_media(media.photo, bytes)
                return Image.open(io.BytesIO(buffer))
            
            logger.warning(f"⚠️ @{username}'s latest story is not a photo!")
        else:
            logger.warning(f"⚠️ @{username} has no stories!")
    except Exception as e:
        logger.error(f"❌ Error fetching story for @{username}: {e}")
    return None

def verify_user_story(username, similarity_score):
    headers = {"X-Auth-Key": X_AUTH_KEY}
    try:
        logger.info(f"🔗 Sending verification (GET) request for @{username} to {VERIFY_STORY_URL.format(username=username)}")
        response = requests.get(VERIFY_STORY_URL.format(username=username), headers=headers)
        logger.info(f"🔗 Verification Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            logger.info(f"✅ Verification successful for @{username}")
            return True

        logger.error(f"❌ Verification failed for @{username}: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Error during verification of @{username}: {e}")
    return False

def get_initial_story_image(username):
    # Replace this with the actual logic to fetch initial images for specific users
    return "https://i.imgur.com/HcUg3Bm.jpeg"

def download_image(url):
    try:
        logger.info(f"📥 Downloading image: {url}")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
        logger.error(f"⚠️ Image download failed! HTTP Status: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Error downloading image: {e}")
    return None

def compare_images(img1, img2, threshold=0.6):
    img1 = cv2.cvtColor(np.array(img1), cv2.COLOR_RGB2GRAY)
    img2 = cv2.cvtColor(np.array(img2), cv2.COLOR_RGB2GRAY)
    img1 = cv2.resize(img1, (img2.shape[1], img2.shape[0]))

    similarity, _ = ssim(img1, img2, full=True)
    logger.info(f"📊 Image similarity score: {similarity:.2f}")
    return similarity, similarity >= threshold

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
