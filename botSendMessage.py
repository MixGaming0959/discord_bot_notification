from random import randint
from dotenv import load_dotenv  # type: ignore
from os import environ
from requests import post as requests_post # type: ignore

import asyncio
from datetime import datetime, time

load_dotenv()
def load_env(key:str):
    return environ.get(key)
def str_to_bool(s:str) -> bool: 
    return s in ['true', '1', 'yes', 1, True]
def random_color():
    # Generate a random color as an integer value
    return int(randint(0, 0xFFFFFF))

# Constants
WEBHOOK_URL = load_env("WEBHOOK_URL")
WEBHOOK_PORT = load_env("WEBHOOK_PORT")
PUBSUBHUBBUB_URL = load_env("PUBSUBHUBBUB_URL")
YOUTUBE_API_KEY = load_env("YOUTUBE_API_KEY")
DISCORD_BOT_TOKEN = load_env("DISCORD_BOT_TOKEN")
PROCESSED_PAYLOADS = list()
LIMIT_TIME_LIFE = 20 # Seconds

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

def get_live_videos():
    result = asyncio.run(liveStreamStatus.get_live_stream_30())
    vtuber_id = set()
    gen_id = set()
    group_id = set()

    for r in result:
        vtuber_id = set()
        gen_id = set()
        group_id = set()
        vtuber = db.getVtuber(r["channel_id"])
        vtuber_id.add(vtuber["id"])
        gen_id.add(vtuber["gen_id"])
        group_id.add(vtuber["group_id"])
        if r['colaborator'] != None:
            r['colaborator'] = r['colaborator'].split(",")
            for c in r['colaborator']:
                vtuber_tmp = db.getVtuber(c)
                if vtuber_tmp == None:
                    continue
                vtuber_id.add(vtuber_tmp["id"])
                gen_id.add(vtuber_tmp["gen_id"])
                group_id.add(vtuber_tmp["group_id"])
    
        discord_channel = db.getDiscordDetails(list(vtuber_id), list(gen_id), list(group_id))
        for d in discord_channel:
            if d["channel_id"] == None:
                continue
            send_embed(d["channel_id"], [r])

    return "OK", 200

def send_embed(channel_id, data: list):
    """Send an embed to a channel."""
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
    }

    embeds = create_embed(data)
    response = requests_post(url, headers=headers, json=embeds)
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

def loop():
    print("Start Loop")
    while True:
        get_live_videos()
        asyncio.run(asyncio.sleep(60 * 10))


if __name__ == "__main__":
    loop()