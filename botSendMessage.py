from random import randint
from requests import post as requests_post # type: ignore
import asyncio
from datetime import datetime, time

from get_env import GetEnv
from database import DatabaseManager
from fetchData import LiveStreamStatus
# env = GetEnv()

def random_color():
    # Generate a random color as an integer value
    return int(randint(0, 0xFFFFFF))


class BotSendMessage:
    def __init__(self, discord_token: str):
        env = GetEnv()

        self.WEBHOOK_URL = env.webhook_url_env()
        self.WEBHOOK_PORT = env.webhook_port_env()
        self.YOUTUBE_API_KEY = env.youtube_api_key_env()
        self.DISCORD_BOT_TOKEN = discord_token
        self.BEFORE_LIVE = env.get_env_int('BEFORE_LIVE')
        self.PUBSUBHUBBUB_URL = env.get_env_str("PUBSUBHUBBUB_URL")
        self.PROCESSED_PAYLOADS = list()
        self.LIMIT_TIME_LIFE = 20 # Seconds
        self.SEND_MSG_WHEN_START = env.get_env_bool('SEND_MSG_WHEN_START')
        # Database

        db_path = env.get_env_str('DB_PATH')
        self.db = DatabaseManager(db_path)
        self.AUTO_CHECK = env.get_env_int('AUTO_CHECK')
        self.ISUPDATE_PATH = env.get_env_str('ISUPDATE_PATH')
        self.MAX_EMBED_SIZE = 4000

        self.liveStreamStatus = LiveStreamStatus(db_path, self.AUTO_CHECK)

    def get_live_videos(self):
        result = asyncio.run(self.liveStreamStatus.get_before_live_stream())
        vtuber_id = set()
        gen_id = set()
        group_id = set()

        for r in result:
            vtuber_id = set()
            gen_id = set()
            group_id = set()
            vtuber = self.db.getVtuber(r["channel_id"])
            vtuber_id.add(vtuber["id"])
            gen_id.add(vtuber["gen_id"])
            group_id.add(vtuber["group_id"])
            if r['colaborator'] != None:
                r['colaborator'] = r['colaborator'].split(",")
                for c in r['colaborator']:
                    vtuber_tmp = self.db.getVtuber(c)
                    if vtuber_tmp == None:
                        continue
                    vtuber_id.add(vtuber_tmp["id"])
                    gen_id.add(vtuber_tmp["gen_id"])
                    group_id.add(vtuber_tmp["group_id"])
        
            discord_details = self.db.getDiscordDetails(list(vtuber_id), list(gen_id), list(group_id))
            for d in set(tuple(d.items()) for d in discord_details):
                dic = dict(d)
                if dic["is_PreAlertEnabled"] == 0:
                    continue
                if dic["channel_id"] == None:
                    continue
                self.send_embed(dic["channel_id"], [r])
                # print(f"Embed sent to {d['channel_id']} for {r['title']}")

        return "OK", 200

    def send_embed(self, channel_id, data: list):
        """Send an embed to a channel."""
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bot {self.DISCORD_BOT_TOKEN}",
        }

        embeds = self.create_embed(data)
        response = requests_post(url, headers=headers, json=embeds)
        if response.status_code == 200:
            print("BotSendMSG: Embed sent successfully.")
            return {"status": "success", "message": "Embed sent successfully"}
        else:
            print(f"BotSendMSG: Failed to send embed. Status code: {response.status_code}")
            return {"status": "failed", "message": f"Error: {response.status_code}"}


    # embed as http send response
    def create_embed(self, data: list):
        result = {
            # "content": "แจ้งเตือนก่อนไลฟ์ 30 นาที",
            "embeds": []}
        vtuber_image = self.db.getVtuber(data[0]["channel_id"])['image']
        for v in data:
            # print(v)
            url = v["url"]
            image = v["image"]
            if type(v["start_at"]) == str:
                v["start_at"] = datetime.fromisoformat(v["start_at"])
                start_at = v["start_at"].strftime('%H:%M')
            else:
                start_at = v["start_at"].strftime('%H:%M')
            # start_at = (datetime.strptime(v['start_at'], "%Y-%m-%d %H:%M:%S")).strftime('%H:%M')
            # now - start_at to hour and minute
            dt = self.db.datetime_gmt(v["start_at"]) - self.db.datetime_gmt(datetime.now())
            hour, minute = dt.seconds // 3600, (dt.seconds // 60) % 60

            timeStr = ""
            if hour > 0:
                timeStr += f"{hour} ชั่วโมง "
            if minute > 0:
                timeStr += f"{minute} นาที"
            if timeStr == "":
                timeStr = "0 นาที"
            

            title = v["title"] + f" กำลังจะเริ่มไลฟ์ในอีก {timeStr} นาที"
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

    def run_send_message(self):
        print("BotSendMSG: Start Loop")
        while True:
            self.get_live_videos()
            asyncio.run(asyncio.sleep(60))


if __name__ == "__main__":
    bot = BotSendMessage()

    bot.run_send_message()