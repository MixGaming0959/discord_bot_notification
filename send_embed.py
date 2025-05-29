
from datetime import datetime
from random import randint
import requests
from database import DatabaseManager
from math import ceil as RoundUp

class DiscordSendData:
    def __init__(self, discord_bot_token, db: DatabaseManager):
        self.discord_bot_token = discord_bot_token
        self.db = db

    def send_message(self, channel_id, message):
        """Send a message to a channel."""
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        headers = {
            "Content-Type": "applicationdiscord_bot_token/json",
            "Authorization": f"Bot {self.discord_bot_token}",
        }
        data = {"content": message}
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            print("WebhookApp: Message sent successfully.")
            # sys.stdout.flush()
            return {"status": "success", "message": "Message sent successfully"}
        else:
            print(f"WebhookApp: Failed to send message. Status code: {response.status_code}")
            # sys.stdout.flush()
            return {"status": "failed", "message": f"Error: {response.status_code}"}


    def send_embed(self, channel_id: str, data: list, type_embed:str = ("live, before")):
        """Send an embed to a channel."""
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bot {self.discord_bot_token}",
        }
        if type_embed == "live":
            embeds = self.create_embed_live(data)
        elif type_embed == "before":
            embeds = self.create_embed_before(data)
        else:
            embeds = self.create_embed_live(data)

        response = requests.post(url, headers=headers, json=embeds)
        if response.status_code == 200:
            # print("WebhookApp: successfully.")
            # sys.stdout.flush()
            return {"status": "success", "message": "Embed sent successfully"}
        else:
            print(f"WebhookApp: Failed. Status code: {response.status_code}")
            # sys.stdout.flush()
            return {"status": "failed", "message": f"Error: {response.status_code}"}

    # embed as http send response
    def create_embed_live(self, data: list):
        result = {"embeds": []}
        vtuber_image = self.db.getVtuber(data[0]["channel_id"])['image']
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
                "description": f"{title} [Link]({url})", # 10 December 2024
                "color": self.random_color(),
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
    
    # # embed as http send response
    def create_embed_before(self, data: list):
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

            start_at_check = self.db.datetime_gmt(v["start_at"])
            timeNow = self.db.datetime_gmt(datetime.now())
            if start_at_check < timeNow:
                continue
            dt = start_at_check - timeNow

            hour, minute = dt.seconds // 3600, RoundUp(dt.seconds / 60) % 60
            # 1 ชั่วโมง 59 นาที -> 2 ชั่วโมง
            if minute == 0:
                hour = RoundUp(dt.seconds / 3600)

            timeStr = ""
            if hour > 0:
                timeStr += f"{hour} ชั่วโมง "
            if minute > 0:
                timeStr += f"{minute} นาที"
            if timeStr == "":
                timeStr = "0 นาที"
            
            title = v["title"] + f" กำลังจะเริ่มไลฟ์ในอีก {timeStr}"
            channel_name = v["channel_name"]
            channel_tag = v["channel_tag"]
            live_status = v["live_status"]
            channel_link = f"https://www.youtube.com/@{channel_tag}/streams"
            
            embed = {
                "title": channel_name,
                # "description": f"ตารางไลฟ์ ประจำวันที่ {v['start_at'].strftime('%d %B %Y')}", # 10 December 2024
                "description": f"{title} [Link]({url})", # 10 December 2024
                "color": self.random_color(),
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

    def random_color(self):
        # Generate a random color as an integer value
        return int(randint(0, 0xFFFFFF))