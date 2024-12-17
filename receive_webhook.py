from random import randint
from threading import Timer
# from flask import Flask, request  # type: ignore
import requests # type: ignore
import xml.etree.ElementTree as ET
from get_env import GetEnv  # type: ignore

import asyncio
from datetime import datetime, timedelta

from bottle import Bottle, request, response

app = Bottle()

env = GetEnv()
# Constants
WEBHOOK_URL = env.webhook_url_env()
WEBHOOK_PORT = env.webhook_port_env()
YOUTUBE_API_KEY = env.youtube_api_key_env()
DISCORD_BOT_TOKEN = env.discord_token_env()

LIMIT_TIME_LIFE = 20 # Seconds
PROCESSED_PAYLOADS = list()

# str to bool
SEND_MSG_WHEN_START = env.get_env_bool('SEND_MSG_WHEN_START')
# Database
from database import DatabaseManager

db_path = env.get_env_str('DB_PATH')
db = DatabaseManager(db_path)
AUTO_CHECK = env.get_env_int('AUTO_CHECK')
ISUPDATE_PATH = env.get_env_str('ISUPDATE_PATH')
MAX_EMBED_SIZE = 4000

# FetchData
from fetchData import LiveStreamStatus
liveStreamStatus = LiveStreamStatus(db_path, AUTO_CHECK)

@app.route('/api/v1/webhooks', method=['GET', 'POST'])
def webhooks():
    if request.method == 'GET':
        # Verification
        hub_challenge = request.query.get('hub.challenge')
        if hub_challenge:
            return hub_challenge
        response.status = 400
        return "Invalid request"

    elif request.method == 'POST':
        # Handle notifications
        notification = request.body.read()  # อ่านข้อมูลจาก POST Request
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
                        print(f"WebhookApp: https://youtube.com/watch?v={video_id} is already processed. Skipping.")
                        return "OK"
                PROCESSED_PAYLOADS.append(target)    

                Timer(20, wait_result, args=(video_id, channel_id)).start()
            else:
                print(f"WebhookApp: {channel_name} https://youtube.com/watch?v={video_id}; Notification is older than 7 days. Skipping.")
        else:
            print("WebhookApp: No valid video or channel ID found in the notification.")
        return "OK"

def wait_result(video_id, channel_id):
    result = asyncio.run(liveStreamStatus.get_live_stream_info(video_id, channel_id))
    # print(db.datetime_gmt(datetime.now()), video_id, channel_id, result)
    function(video_id, result)

def function(video_id:str, result:list, loop:int= 0):
    if result and loop < 2:
        insertLiveTable(result.copy())

        for v in result:
            timeNow = db.datetime_gmt(datetime.now())
            vtuber_ids = set()
            gen_ids = set()
            group_ids = set()
            print(f"WebhookApp: Start at {v['start_at']} https://youtube.com/watch?v={video_id} is live or upcoming.")
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
            live_status = v['live_status'] == "live" and parse_datetime(timedelta(minutes=60), db.datetime_gmt(v['start_at']), timedelta(minutes=10))
            upcoming_status = v['live_status'] == "upcoming" and parse_datetime(timedelta(minutes=10), db.datetime_gmt(v['start_at']), timedelta(minutes=30))

            if (live_status or upcoming_status) and SEND_MSG_WHEN_START:
                discord_details = db.getDiscordDetails(list(vtuber_ids), list(gen_ids), list(group_ids))
                for detail in set(tuple(d.items()) for d in discord_details):
                    dic = dict(detail)
                    if dic['is_NotifyOnLiveStart'] == 0:
                        continue
                    
                    if v['live_status'] == "live" or v['start_at'] < timeNow:
                        v['start_at'] = timeNow
                    send_embed(dic['channel_id'], [v])
            elif SEND_MSG_WHEN_START:
                loop += 1
                Timer(5, function, args=(video_id, result, loop)).start()
                print(f"WebhookApp: Start at {v['start_at']} https://youtube.com/watch?v={video_id} is already more than 15 minutes live or upcoming. Skipping.")
    else:
        print(f"WebhookApp: https://www.youtube.com/watch?v={video_id} is End. Skipping.")

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
            print("WebhookApp: Raw notification received:", notification.decode("utf-8"))
    except Exception as e:
        print(f"WebhookApp: Error parsing notification: {e}")
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
        print("WebhookApp: Message sent successfully.")
        return {"status": "success", "message": "Message sent successfully"}
    else:
        print(f"WebhookApp: Failed to send message. Status code: {response.status_code}")
        return {"status": "failed", "message": f"Error: {response.status_code}"}


def send_embed(channel_id: str, data: list):
    """Send an embed to a channel."""
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
    }

    embeds = create_embed(data)
    response = requests.post(url, headers=headers, json=embeds)
    if response.status_code == 200:
        print("WebhookApp: successfully.")
        return {"status": "success", "message": "Embed sent successfully"}
    else:
        print(f"WebhookApp: Failed. Status code: {response.status_code}")
        return {"status": "failed", "message": f"Error: {response.status_code}"}

# embed as http send response
def create_embed(data: list):
    result = {"embeds": []}
    vtuber_image = db.getVtuber(data[0]["channel_id"])['image']
    for v in data:
        # print(v)
        title = v["title"] + " กำลังไลฟ์"
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
            # "description": f"ตารางไลฟ์ ประจำวันที่ {v['start_at'].strftime('%d %B %Y')}", # 10 December 2024
            "description": f"{title} [Link]({url})", # 10 December 2024
            "color": random_color(),
            "thumbnail": {"url": vtuber_image},
            "image": {"url": image},
            "fields": [
                # {
                #     "name": "ชื่อไลฟ์",
                #     "value": f"{title} [Link]({url})",
                #     "inline": False,
                # },
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

def random_color():
    # Generate a random color as an integer value
    return int(randint(0, 0xFFFFFF))

def run_server():
    app.run(host="0.0.0.0", port=WEBHOOK_PORT)
        

if __name__ == "__main__":

    # Timer(0, loop_get_live_videos, args=()).start()

    run_server()
