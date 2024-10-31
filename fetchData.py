import asyncio
from datetime import datetime, timezone, timedelta
from database import DatabaseManager
from googleapiclient.discovery import build  # type: ignore


# ใส่ API Key ที่สร้างไว้
api_key = "AIzaSyCOozAoiqbvpwNzbXhsDkx_I1lMMo_jafM"

class LiveStreamStatus():
    def __init__(self, db_path:str, autoUpdate: bool = False):
        self.db = DatabaseManager(db_path)
        self.autoUpdate = autoUpdate

    async def live_stream_status(self):
        result = []
        try:
            youtube = build("youtube", "v3", developerKey=api_key)

            # ค้นหาวิดีโอล่าสุดของ Channel
            request_live = youtube.search().list(
                part="snippet",
                channelId=self.channel_id,
                type="video",
                eventType="live",
                maxResults=2,
            )

            request_upcoming = youtube.search().list(
                part="snippet",
                channelId=self.channel_id,
                type="video",
                eventType="upcoming",
                maxResults=7,
            )

            response_live = request_live.execute()
            response_upcoming = request_upcoming.execute()

            response = response_live
            response["items"] += response_upcoming["items"]

            # with open("data.json", "w") as outfile:
            #     json.dump(response, outfile)

            # ตรวจสอบสถานะการถ่ายทอดสด
            if "items" in response and response["items"]:
                for item in response["items"]:
                    if item["snippet"]["liveBroadcastContent"] == "none":
                        continue
                    video_id = item["id"]["videoId"]
                    video_details = await self.get_live_stream_info(video_id)
                    if video_details == None:
                        continue

                    result.append(video_details)
            else:
                print("No live or upcoming broadcasts found.")
            if len(result) == 0:
                return None
            # เพิ่มข้อมูลลงในฐานข้อมูล
            for data in result:
                self.db.checkLiveTable(data)

        except Exception as e:
            print(e)
        return result

    async def get_live_stream_info(self, video_id):
        vtuber = self.db.getVtuber(self.channel_id)
        try:
            youtube = build("youtube", "v3", developerKey=api_key)

            if "https://www.youtube.com/watch?v=" in video_id:
                video_id = video_id.replace("https://www.youtube.com/watch?v=", "")
            # ขอข้อมูลของวิดีโอที่กำหนด
            request = youtube.videos().list(
                part="liveStreamingDetails,snippet,status", id=video_id
            )

            response = request.execute()
            # with open("video_detail.json", "w") as outfile:
            #     json.dump(response, outfile)

        except Exception as e:
            print(e)
            return None

        if "items" in response and response["items"]:
            video_status = response['items'][0]['status']
            privacy_status = video_status.get('privacyStatus', 'unknown')

            # ตรวจสอบว่าสถานะเป็นส่วนตัวหรือไม่
            if privacy_status == 'private':
                self.db.cancelLiveTable(f"https://www.youtube.com/watch?v={video_id}", "private")
            elif privacy_status == 'public':
                pass
            elif privacy_status == 'unlisted':
                pass
            else:
                self.db.cancelLiveTable(f"https://www.youtube.com/watch?v={video_id}", "unknown")

            video_details = response["items"][0]
            snippet = video_details["snippet"]

            title = snippet["title"]
            video_id = video_details["id"]
            if "maxres" in snippet["thumbnails"]:
                image = snippet["thumbnails"]["maxres"]["url"]
            elif "high" in snippet["thumbnails"]:
                image = snippet["thumbnails"]["high"]["url"]
            elif "medium" in snippet["thumbnails"]:
                image = snippet["thumbnails"]["medium"]["url"]
            else:
                image = snippet["thumbnails"]["default"]["url"]
            live_status = snippet["liveBroadcastContent"]
            channel_name = snippet["channelTitle"]

            colaborator = None
            if "@" in title:
                tmp = title[title.strip().index("@") :]
                colaborator = ",".join(tmp.split("@")[1:])
            elif "ft." in title.lower():
                tmp = title.lower()
                tmp = title[tmp.strip().index("ft.") + 3 :]
                colaborator = ""
                for i in tmp.split(","):
                    if i.strip() == "":
                        continue
                    name = self.db.getVtuber(i.strip())
                    if name == None:
                        colaborator += f"{i.strip()},"
                    else:
                        colaborator += f"{name[0]['channel_tag']},"
                colaborator = colaborator[:-1]

            data = {
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "start_at": None,
                "colaborator": colaborator,
                "vtuber_id": vtuber["id"],
                "image": image,
                "live_status": live_status,
                "channel_name": channel_name,
                "channel_tag": vtuber["channel_tag"],
                "channel_id": self.channel_id,
            }

            # ตรวจสอบเวลาเริ่มและสถานะการถ่ายทอดสด
            live_details = video_details["liveStreamingDetails"]
            if "actualStartTime" in live_details:
                # ถ้าเริ่มถ่ายทอดสดแล้ว แปลงเวลาที่เริ่มเป็น datetime object
                start_at = datetime.fromisoformat(
                    live_details["actualStartTime"][:-1]
                ).replace(tzinfo=timezone.utc)
                data["start_at"] = start_at
                # current_time = datetime.now(timezone.utc)
                # elapsed_time = current_time - actual_start_time
                # print(f"Live started {elapsed_time.total_seconds() // 60} minutes ago.")

            elif "scheduledStartTime" in live_details:
                # ถ้ายังไม่เริ่มถ่ายทอดสด ดูเวลาที่ตั้งไว้สำหรับเริ่ม
                start_at = datetime.fromisoformat(
                    live_details["scheduledStartTime"][:-1]
                ).replace(tzinfo=timezone.utc)

                # print(f"Live is scheduled to start at {scheduled_start_time.strftime('%Y-%m-%d %H:%M:%S%z %Z')}.")
            else:
                return None

            # แปลงเวลาเป็นเวลาประเทศไทย
            tz = timezone(timedelta(hours=7))
            new_time = start_at.astimezone(tz)
            data["start_at"] = new_time
            return data
        else:
            self.db.cancelLiveTable(f"https://www.youtube.com/watch?v={video_id}", "cancelled")
            print(vtuber["name"],f"https://www.youtube.com/watch?v={video_id}")
            return None

    def set_channel_id(self, channel_id:str):
        self.channel_id = channel_id

    async def get_live_stream(self, channel_tag: str):
        video = self.db.getLiveTable(channel_tag)
        
        result = []
        # ตรวจสอบว่าเริ่มถ่ายทอดสดหรือยัง
        if video == None:
            return result
        for data in video:
            video_details = {}
            dt = datetime.fromisoformat(data["start_at"])
            data["start_at"] = datetime.strptime(
                dt.strftime("%Y-%m-%d %H:%M:%S%z"), "%Y-%m-%d %H:%M:%S%z"
            )

            if self.autoUpdate and (data["live_status"] == "upcoming" and data["start_at"] < self.db.datetime_gmt(datetime.now())):
                self.channel_id = data["channel_id"]
                video_details = await self.get_live_stream_info(data["url"])
                # เช็คว่า Liveหรือยัง มีการเปลี่ยนคอนเทนต์หรือไม่
                if video_details != None and (
                    data["title"] != video_details["title"]
                    or data["image"] != video_details["image"]
                    or data["start_at"] != video_details["start_at"]
                ):
                    self.db.updateLiveTable(video_details)
                else:
                    video_details = data
            else:
                video_details = data
            result.append(video_details)

        return result

    async def check_live_status(self, channel_tag: str):
        video = self.db.getLiveTable(channel_tag)
        
        # ตรวจสอบว่าเริ่มถ่ายทอดสดหรือยัง
        if video == None:
            return f"ไม่มีการอัพเดทข้อมูลตาราง {channel_tag}..."
        for data in video:
            dt = datetime.fromisoformat(data["start_at"])
            data["start_at"] = datetime.strptime(
                dt.strftime("%Y-%m-%d"), "%Y-%m-%d"
            )
            timeNow = datetime.strptime(
                self.db.datetime_gmt(datetime.now()).strftime("%Y-%m-%d"), "%Y-%m-%d"
            )

            if self.autoUpdate and (data["live_status"] == "upcoming" and data["start_at"] >= timeNow):
                self.channel_id = data["channel_id"]
                video_details = await self.get_live_stream_info(data["url"])
                # เช็คว่า Liveหรือยัง มีการเปลี่ยนคอนเทนต์หรือไม่
                if video_details != None and (
                    data["title"] != video_details["title"]
                    or data["image"] != video_details["image"]
                    or data["start_at"] != video_details["start_at"]
                ):
                    self.db.updateLiveTable(video_details)
        return f"อัพเดทข้อมูลตาราง {channel_tag} สําเร็จ..."

if __name__ == "__main__":
    # ใส่ Channel ID ที่ต้องการตรวจสอบ
    from Encrypt import Encrypt
    from dotenv import load_dotenv # type: ignore
    from os import environ

    load_dotenv()

    de = Encrypt()
    db_path = de.decrypt(environ.get('DB_PATH'))
    db = DatabaseManager(db_path)
    AUTO_UPDATE = False
    liveStreamStatus = LiveStreamStatus(db_path, AUTO_UPDATE)

    listVtuber = liveStreamStatus.db.listVtuberByGroup("Pixela")
    for _, v in enumerate(listVtuber):
        liveStreamStatus.set_channel_id(v["channel_id"])
        asyncio.run(liveStreamStatus.live_stream_status())

