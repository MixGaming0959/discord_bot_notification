from random import randint
from threading import Timer
from flask import Flask, request
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv  # type: ignore
from os import environ

import asyncio
from datetime import datetime, timedelta

app = Flask(__name__)
load_dotenv()
def load_env(key:str):
    return environ.get(key)
def str_to_bool(s:str) -> bool: 
    return s in ['true', '1', 'yes', 1, True]

# Constants
WEBHOOK_URL = load_env("WEBHOOK_URL")
WEBHOOK_PORT = load_env("WEBHOOK_PORT")
PUBSUBHUBBUB_URL = load_env("PUBSUBHUBBUB_URL")
YOUTUBE_API_KEY = load_env("YOUTUBE_API_KEY")
DISCORD_BOT_TOKEN = load_env("DISCORD_BOT_TOKEN")
PROCESSED_PAYLOADS = list()
LIMIT_TIME_LIFE = 20 # Seconds
ALREADY_LIVE = 60 # minutes
BEFORE_LIVE = 450 # minutes

# str to bool
SEND_MSG_WHEN_START = str_to_bool(load_env('SEND_MSG_WHEN_START'))
# Database
from database import DatabaseManager

db_path = load_env('DB_PATH')
db = DatabaseManager(db_path)
AUTO_CHECK = int(load_env('AUTO_CHECK') or 0)
ISUPDATE_PATH = load_env('ISUPDATE_PATH')
MAX_EMBED_SIZE = 4000

# FetchData
from fetchData import LiveStreamStatus
liveStreamStatus = LiveStreamStatus(db_path, AUTO_CHECK)

API_ROUTE = ""

@app.route("/api/v1/webhooks", methods=["GET", "POST"])
def webhooks():
    if request.method == "GET":
        # Verification
        hub_challenge = request.args.get("hub.challenge")
        if hub_challenge:
            return hub_challenge, 200
        return "Invalid request", 400

    elif request.method == "POST":
        # Handle notifications
        notification = request.data
        # print("Raw notification received:", notification.decode("utf-8"))

        # Parse notification for channel ID and video ID
        video_id, channel_id, updated, channel_name = parse_notification(notification)
        if video_id and channel_id and updated and channel_name:
            if updated > db.datetime_gmt(datetime.now() - timedelta(days=7)):

                current_time = db.datetime_gmt(datetime.now())
                target = {
                    "video_id": video_id,
                    "channel_id": channel_id,
                    "timestamp": current_time
                }

                # Update processed payloads
                global PROCESSED_PAYLOADS
                PROCESSED_PAYLOADS = [
                    p for p in PROCESSED_PAYLOADS if p["timestamp"] > current_time - timedelta(seconds=LIMIT_TIME_LIFE)
                ]

                # Check
                for recent in PROCESSED_PAYLOADS:
                    if recent["video_id"] == video_id and recent["channel_id"] == channel_id and parse_datetime(timedelta(seconds=LIMIT_TIME_LIFE), recent["timestamp"], timedelta(seconds=LIMIT_TIME_LIFE)):
                        print(f"https://youtube.com/watch?v={video_id} is already processed. Skipping.")
                        return "OK", 200
                PROCESSED_PAYLOADS.append(target)    

                Timer(2, wait_result, args=(video_id, channel_id)).start()
            else:
                print(f"{channel_name} https://youtube.com/watch?v={video_id}; Notification is older than 7 days. Skipping.")
        else:
            print("No valid video or channel ID found in the notification.")
        return "OK", 200

def wait_result(video_id, channel_id):
    result = asyncio.run(liveStreamStatus.get_live_stream_info(video_id, channel_id))
    # print(db.datetime_gmt(datetime.now()), video_id, channel_id, result)
    function(video_id, result)

def function(video_id:str, result:list, loop:int= 0):
    if result and loop < 2:
        insertLiveTable(result.copy())

        for v in result:
            vtuber_ids = set()
            gen_ids = set()
            group_ids = set()
            print(v['channel_name'], v['live_status'], v['url'])
            if type(v['start_at']) == str:
                v['start_at'] = db.datetime_gmt(datetime.fromisoformat(v['start_at']))
            vtuber = db.getVtuber(v['channel_tag'])
            vtuber_ids.add(vtuber['id'])
            gen_ids.add(vtuber['gen_id'])
            group_ids.add(vtuber['group_id'])
            if v['colaborator']:
                for c in v['colaborator'].split(","):
                    colab = db.getVtuber(c)
                    if colab:
                        vtuber_ids.add(colab['id'])
                        gen_ids.add(colab['gen_id'])
                        group_ids.add(colab['group_id'])
            live_status = v['live_status'] == "live" and parse_datetime(timedelta(minutes=ALREADY_LIVE), db.datetime_gmt(v['start_at']), timedelta(minutes=10))
            upcoming_status = v['live_status'] == "upcoming" and parse_datetime(timedelta(minutes=10), db.datetime_gmt(v['start_at']), timedelta(minutes=BEFORE_LIVE))
            # print(live_status, upcoming_status, v['live_status'])
            if (live_status or upcoming_status) and SEND_MSG_WHEN_START:
                discord_details = db.getDiscordDetails(list(vtuber_ids), list(gen_ids), list(group_ids))
                for detail in set(tuple(d.items()) for d in discord_details):
                    dic = dict(detail)
                    send_embed(dic['channel_id'], [v])
            elif SEND_MSG_WHEN_START:
                loop += 1
                Timer(5, function, args=(video_id, result, loop)).start()
                print(f"Start at {v['start_at']} https://youtube.com/watch?v={video_id} is already more than 15 minutes live or upcoming. Skipping.")
    else:
        print(f"https://www.youtube.com/watch?v={video_id} is End. Skipping.")

async def wait_for_notification():
    await asyncio.sleep(1)

def truncate_date(date_str: str, date_format="%Y-%m-%dT%H:%M:%S%z") -> datetime:
    if "." in date_str:
        reversed_date_str = date_str[::-1]
        if "+" in reversed_date_str:
            reversed_date_str = reversed_date_str[:reversed_date_str.index("+")+1]
        else:
            reversed_date_str = reversed_date_str[:reversed_date_str.index("-")+1]
        date_str = date_str[:date_str.index(".")] + reversed_date_str[::-1]

    return datetime.strptime(date_str, date_format)

def parse_datetime(past_timedelta: timedelta, target_date: datetime, future_timedelta: int) -> bool:
    current_time = db.datetime_gmt(datetime.now())
    # print("parse_datetime: ", current_time - past_timedelta , target_date ,  current_time + future_timedelta)
    return current_time - past_timedelta <= target_date and target_date <= current_time + future_timedelta

def parse_notification(notification):
    """Parse the Atom feed to extract video ID and channel ID."""
    try:
        root = ET.fromstring(notification)
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        video_id = root.find(".//atom:entry/atom:id", namespace)
        channel_id   = root.find(".//atom:entry/atom:author/atom:uri", namespace)
        channel_name = root.find(".//atom:entry/atom:author/atom:name", namespace)
        updated = root.find(".//atom:entry/atom:updated", namespace)
        if updated is not None:
            updated = db.datetime_gmt(truncate_date(updated.text))
        else:
            updated = db.datetime_gmt(datetime.now())

        if video_id is not None and channel_id is not None and channel_name is not None and updated is not None:
            video_id = video_id.text.split(":")[-1]
            channel_id = channel_id.text.split("/")[-1] 
            channel_name = channel_name.text
            return video_id, channel_id, updated, channel_name
        else:
            print("Raw notification received:", notification.decode("utf-8"))
    except Exception as e:
        print(f"Error parsing notification: {e}")
    return None, None, None, None

def insertLiveTable(video_details: list):
    copy = video_details.copy()
    for data in copy:
        data['is_noti'] = True
        db.checkLiveTable(data)

def send_message(channel_id, message):
    """Send a message to a channel."""
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
    }
    data = {"content": message}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print("Message sent successfully.")
    else:
        print(f"Failed to send message. Status code: {response.status_code}")


def send_embed(channel_id, data: list):
    """Send an embed to a channel."""
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
    }

    embeds = create_embed(data)
    response = requests.post(url, headers=headers, json=embeds)
    if response.status_code == 200:
        print("Embed sent successfully.")
    else:
        print(f"Failed to send embed. Status code: {response.status_code}")


# embed as http send response
def create_embed(data: list):
    result = {"embeds": []}
    vtuber_image = db.getVtuber(data[0]["channel_id"])['image']
    for v in data:
        # print(v)
        title = v["title"]
        url = v["url"]
        image = v["image"]
        if type(v["start_at"]) == str:
            v["start_at"] = datetime.fromisoformat(v["start_at"])
            start_at = v["start_at"].strftime('%H:%M')
        else:
            start_at = v["start_at"].strftime('%H:%M')
        # start_at = (datetime.strptime(v['start_at'], "%Y-%m-%d %H:%M:%S")).strftime('%H:%M')

        channel_name = v["channel_name"]
        channel_tag = v["channel_tag"]
        live_status = v["live_status"]
        channel_link = f"https://www.youtube.com/@{channel_tag}/streams"
        
        embed = {
            "title": channel_name,
            "description": f"ตารางไลฟ์ ประจำวันที่ {v['start_at'].strftime('%d %B %Y')}", # 10 December 2024
            "color": random_color(),
            "thumbnail": {"url": vtuber_image},
            "image": {"url": image},
            "fields": [
                {
                    "name": "ชื่อไลฟ์",
                    "value": f"{title} [Link]({url})",
                    "inline": False,
                },
                {
                    "name": "เวลาไลฟ์",
                    "value": f"{start_at} น.",
                    "inline": True,
                },
                {
                    "name": "สถานะ",
                    "value": live_status,
                    "inline": True,
                },
                {
                    "name": "ที่ช่อง",
                    "value": f"[{channel_tag}]({channel_link})",
                    "inline": True,
                },
            ],
        }
        result["embeds"].append(embed)
    return result


def subscribe_to_channel(channel_id, callback_url, subscribe):
    """Subscribe to a YouTube channel's feed."""
    topic_url = f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel_id}"
    data = {
        "hub.callback": callback_url,
        "hub.topic": topic_url,
        "hub.mode": subscribe,
        "hub.verify": "async",
    }
    response = requests.post(PUBSUBHUBBUB_URL, data=data)
    if response.status_code != 202 and response.text != "OK":
        print(f"Failed to subscribe to channel {channel_id}. Response: {response.text}")
    else:
        print(f"Subscription request accepted for channel {channel_id}.")

def random_color():
    # Generate a random color as an integer value
    return int(randint(0, 0xFFFFFF))

def run_server():
    app.run(host="0.0.0.0", port=WEBHOOK_PORT)
        

if __name__ == "__main__":

    # Timer(0, loop_get_live_videos, args=()).start()

    run_server()
