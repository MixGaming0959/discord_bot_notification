import requests
from dotenv import load_dotenv  # type: ignore
from os import environ
from database import DatabaseManager 

def load_env(key:str):
    return environ.get(key)

load_dotenv()

db_path = load_env('DB_PATH')
db = DatabaseManager(db_path)
CHANNEL_IDS = []
for v in db.listVtuberByGroup("Pixela"):
    # print(v["channel_tag"], v["channel_id"])
    CHANNEL_IDS.append({"channel_id": v["channel_id"], "channel_tag": v["channel_tag"]})

PUBSUBHUBBUB_URL = load_env("PUBSUBHUBBUB_URL")
WEBHOOK_URL = load_env("WEBHOOK_URL")
OLD_WEBHOOK_PATH = load_env("OLD_WEBHOOK_PATH")

def subscribe_to_channel(channel_details, callback_url, subscribe):
    """Subscribe to a YouTube channel's feed."""
    channel_id = channel_details["channel_id"]
    channel_tag = channel_details["channel_tag"]
    topic_url = f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel_id}"
    data = {
        "hub.callback": callback_url,
        "hub.topic": topic_url,
        "hub.mode": subscribe,
        "hub.verify": "async",
    }
    # print(PUBSUBHUBBUB_URL + " " + str(data))
    try:
        response = requests.post(PUBSUBHUBBUB_URL, data=data)
        if response.status_code != 202:
            print(f"Failed to subscribe to channel {channel_tag}. Response: {response.text}")
        else:
            print(f"{subscribe} request accepted for channel {channel_tag}: {channel_id}.")
    except Exception as e:
        print(f"An error occurred: {e}")

with open(OLD_WEBHOOK_PATH, "r") as file: 
    old_webhook = file.read()
    if old_webhook != WEBHOOK_URL:
        for channel_id in CHANNEL_IDS:
            subscribe_to_channel(channel_id, old_webhook, "unsubscribe")
        for v in CHANNEL_IDS:
            # print(v)
            subscribe_to_channel(v, WEBHOOK_URL, "subscribe")

with open(OLD_WEBHOOK_PATH, "w") as file:
    file.write(WEBHOOK_URL)

