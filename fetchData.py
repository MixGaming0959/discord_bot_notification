import asyncio
import textwrap
from datetime import datetime, timezone, timedelta
import textwrap
from database import DatabaseManager
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore


# ใส่ API Key ที่สร้างไว้
from dotenv import load_dotenv  # type: ignore

load_dotenv()
from os import environ
from Encrypt import Encrypt

api_key = environ.get("YOUTUBE_API_KEY")
TIME_ERROR = timedelta(minutes=30)
LIMIT_TRUNCATE_STRING = 100

class LiveStreamStatus:
    def __init__(self, db_path: str, autoCheck: bool = False):
        self.db = DatabaseManager(db_path)
        self.autoCheck = autoCheck

    async def get_live_stream_info(self, video_ids: str, channel_id: str):
        vtuber = self.db.getVtuber(channel_id)
        try:
            youtube = build("youtube", "v3", developerKey=api_key)

            # ขอข้อมูลของวิดีโอที่กำหนด
            request = youtube.videos().list(
                part="liveStreamingDetails,snippet,status", id=video_ids
            )

            response = request.execute()

            # with open("video_detail.json", "w") as outfile:
            #     import json
            #     json.dump(response, outfile)
            #     print("x")

        except Exception as e:
            print(e)
            return None
        result = []
        lis_video_id = video_ids.split(",")
        if "items" in response and response["items"]:
            for item in response["items"]:
                snippet = item["snippet"]
                live_status = snippet["liveBroadcastContent"]
                video_id = item["id"]
                title = snippet["title"]
                # title contains "Birthday"
                if live_status == "none" and "Birthday" not in title:
                    lis_video_id.remove(video_id)
                    self.db.cancelLiveTable(
                        f"https://www.youtube.com/watch?v={video_id}", "end"
                    )
                    continue

                video_status = item["status"]
                privacy_status = video_status.get("privacyStatus", "unknown")

                # ตรวจสอบว่าสถานะเป็นส่วนตัวหรือไม่
                if privacy_status == "private":
                    self.db.cancelLiveTable(
                        f"https://www.youtube.com/watch?v={video_id}", "private"
                    )
                elif privacy_status == "public":
                    pass
                elif privacy_status == "unlisted":
                    pass
                else:
                    self.db.cancelLiveTable(
                        f"https://www.youtube.com/watch?v={video_id}", "unknown"
                    )

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
                            colaborator += f"{name['channel_tag']},"
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
                    "channel_id": channel_id,
                }

                # ตรวจสอบเวลาเริ่มและสถานะการถ่ายทอดสด
                live_details = item["liveStreamingDetails"] if "liveStreamingDetails" in item else ""
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
                    # now
                    start_at = datetime.now(timezone.utc)

                # แปลงเวลาเป็นเวลาประเทศไทย
                tz = timezone(timedelta(hours=7))
                new_time = start_at.astimezone(tz)
                data["start_at"] = new_time
                lis_video_id.remove(video_id)
                result.append(data)

        if len(lis_video_id) != 0:
            for video_id in lis_video_id:
                self.db.cancelLiveTable(
                    f"https://www.youtube.com/watch?v={video_id}", "cancelled"
                )
            # print(vtuber["name"], f"https://www.youtube.com/watch?v={video_id}")
        
        return result

    def set_channel_id(self, channel_id: str):
        self.channel_id = channel_id

    async def get_live_stream(self, channel_tag: str):
        video = self.db.getLiveTable(channel_tag)

        # เก็บเวลาไลฟ์ แบบ list
        time_list = set()

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
            found = False
            for i in time_list:
                if data["start_at"] - TIME_ERROR <= i <= data["start_at"] + TIME_ERROR:
                    found = True
                    break
            if found:
                continue
            time_list.add(data["start_at"])
            isUpcoming = data["live_status"] in ["upcoming", "live"] and data["start_at"] < self.db.datetime_gmt(datetime.now())
            if self.autoCheck and isUpcoming:
                video_id = data["url"].replace("https://www.youtube.com/watch?v=", "")
                video_details = await self.get_live_stream_info(video_id, data["channel_id"])
                if video_details == None or len(video_details) == 0:
                    continue
                video_details = video_details[0]

                # เช็คว่า Liveหรือยัง มีการเปลี่ยนคอนเทนต์หรือไม่
                if (
                    data["title"] != video_details["title"]
                    or data["image"] != video_details["image"]
                    or data["start_at"] != video_details["start_at"]
                    or data["live_status"] != video_details["live_status"]):
                    print("Update", data["title"], video_details["live_status"])
                    self.db.updateLiveTable(video_details)
                else:
                    video_details = data
            else:
                video_details = data
            video_details['title'] = self.truncate_string(video_details['title'], LIMIT_TRUNCATE_STRING)
            result.append(video_details)

        return result

    def truncate_string(self, s: str, length: int) -> str:
        return textwrap.shorten(s, width=length)

    async def check_channel_status(self, channel_tag: str):
        video = self.db.getLiveTable(channel_tag)

        # เก็บเวลาไลฟ์ แบบ list
        time_list = set()

        # ตรวจสอบว่าเริ่มถ่ายทอดสดหรือยัง
        if video == None:
            return f"ไม่มีการอัพเดทข้อมูลตาราง {channel_tag}..."
        for data in video:
            dt = datetime.fromisoformat(data["start_at"])
            data["start_at"] = datetime.strptime(dt.strftime("%Y-%m-%d"), "%Y-%m-%d")
            timeNow = datetime.strptime(
                self.db.datetime_gmt(datetime.now()).strftime("%Y-%m-%d"), "%Y-%m-%d"
            )

            found = False
            for i in time_list:
                if data["start_at"] - TIME_ERROR <= i <= data["start_at"] + TIME_ERROR:
                    found = True
                    break
            if found:
                continue

            time_list.add(data["start_at"])

            if self.autoCheck and (
                data["live_status"] == "upcoming" and data["start_at"] >= timeNow
            ):
                video_id = data["url"].replace("https://www.youtube.com/watch?v=", "")
                video_details = await self.get_live_stream_info(video_id, data["channel_id"])
                if video_details == None or len(video_details) == 0:
                    continue
                video_details = video_details[0]
                # เช็คว่า Liveหรือยัง มีการเปลี่ยนคอนเทนต์หรือไม่
                if (data["title"] != video_details["title"]
                    or data["image"] != video_details["image"]
                    or data["start_at"] != video_details["start_at"]):
                    self.db.updateLiveTable(video_details)
        return f"อัพเดทข้อมูลตาราง {channel_tag} สําเร็จ..."

    def insert_channel(self, username, gen_name, group_name):
        channel = self.db.getVtuber(username)
        if channel != None:
            raise ValueError(f"ชื่อ {channel['name']} มีอยู่แล้วในฐานข้อมูล...")
        youtube = build("youtube", "v3", developerKey=api_key)

        request = youtube.search().list(
            part="snippet",
            q=username,
            type="channel",
            maxResults=5,  # จำนวนผลลัพธ์ที่ต้องการ
        )

        response = request.execute()

        # แสดงผลชื่อและข้อมูลช่องที่ค้นหาได้
        for item in response["items"]:
            name = item["snippet"]["channelTitle"]
            if self.db.simpleCheckSimilarity(name, username):
                if group_name == "" or gen_name == "":
                    group_name = "Independence"
                    gen_name = "Independence"

                thumbnails = item["snippet"]["thumbnails"]
                image = thumbnails["default"]["url"]
                if "maxres" in thumbnails:
                    image = thumbnails["maxres"]["url"]
                elif "high" in thumbnails:
                    image = thumbnails["high"]["url"]
                elif "medium" in thumbnails:
                    image = thumbnails["medium"]["url"]
                youtube_tag = self.get_channel_tag(item["snippet"]["channelId"])
                data = {
                    "name": name,
                    "gen_name": gen_name,
                    "group_name": group_name,
                    "youtube_tag": youtube_tag,
                    "image": image,
                    "channel_id": item["snippet"]["channelId"],
                }
                self.db.insertVtuber(data)
                return data
            else:
                continue

        raise ValueError(f"ไม่พบช่องที่เกี่ยวข้องกับ {username}")
    
    def get_channel_tag(self, channel_id:str):
        youtube = build('youtube', 'v3', developerKey=api_key)

        # ขอข้อมูล channel โดยใช้ part brandingSettings
        request = youtube.channels().list(
            part='snippet,brandingSettings',
            id=channel_id
        )

        response = request.execute()
        if "items" in response and response["items"]:
            item = response["items"][0]
            customUrl = item["snippet"]["customUrl"]
            return customUrl.replace("@", "")
        else:
            return None

    async def live_stream_status(self, channel_id:str):
        try:
            playlist_id = self.get_channel_info(channel_id)
            if playlist_id == None:
                raise ValueError("Cannot get channel info")

            lis_video_id = self.get_playlist_item(playlist_id, channel_id)
            if lis_video_id == None:
                raise ValueError("Cannot get playlist item")

            video_details = await self.get_live_stream_info(",".join(lis_video_id), channel_id)
            if video_details == None:
                raise ValueError("Cannot get live stream info")

            if len(video_details) == 0:
                # print("No live or upcoming broadcasts found.")
                return None, None

            for data in video_details:
                self.db.checkLiveTable(data)
            return video_details, None
        except HttpError as e:
            error_reason = (
                e.error_details[0]["reason"] if e.error_details else "unknown error"
            )
            raise error_reason
        except Exception as e:
            raise e

    def get_channel_info(self, channel_id:str):
        try: 
            youtube = build("youtube", "v3", developerKey=api_key)
            request = youtube.channels().list(
                part="snippet,contentDetails",
                id=channel_id
            )

            response = request.execute()
        except HttpError as e:
            error_reason = (
                e.error_details[0]["reason"] if e.error_details else "unknown error"
            )
            raise error_reason
        except Exception as e:
            raise e
        playlist_id = ""
        if "items" in response and response["items"]:
            if len(response["items"]) == 1:
                playlist_id = str(response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"])
                return playlist_id
            else:
                for item in response["items"]:
                    if "contentDetails" in item and "relatedPlaylists" in item["contentDetails"] and "uploads" in item["contentDetails"]["relatedPlaylists"]:
                        playlist_id = str(item["contentDetails"]["relatedPlaylists"]["uploads"])
                        return playlist_id
        if playlist_id == "":
            raise ValueError("Cannot get playlist id")

    def get_playlist_item(self, playlist_id:str, channel_id:str):
        try:
            member_playlist = "UUMO" + channel_id[2:]
            youtube = build("youtube", "v3", developerKey=api_key)
            request = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=playlist_id,
                maxResults=10
            )
            response = request.execute()

            request_member = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=member_playlist,
                maxResults=5
            )
            response_member = request_member.execute()
        except HttpError as e:
            error_reason = (
                e.error_details[0]["reason"] if e.error_details else "unknown error"
            )
            raise error_reason
        except Exception as e:
            raise e
        result_video_id = []
        timeBefore = self.db.datetime_gmt(datetime.now() + timedelta(days=10))
        timeAfter = self.db.datetime_gmt(datetime.now() - timedelta(days=10))
        if "items" in response and response["items"]:
            # print("normal")
            for item in response["items"]:
                detail = item["contentDetails"] 
                publishedAt = self.db.datetime_gmt(datetime.strptime(detail["videoPublishedAt"], "%Y-%m-%dT%H:%M:%SZ"))
                if not (publishedAt >= timeAfter and publishedAt <= timeBefore):
                    break
                video_id = str(detail["videoId"])
                result_video_id.append(video_id)

        if "items" in response_member and response_member["items"]:
            # print("member")
            for item in response_member["items"]:
                detail = item["contentDetails"] 
                publishedAt = self.db.datetime_gmt(datetime.strptime(detail["videoPublishedAt"], "%Y-%m-%dT%H:%M:%SZ"))
                if not (publishedAt >= timeAfter and publishedAt <= timeBefore):
                    break
                video_id = str(detail["videoId"])
                result_video_id.append(video_id)

        return result_video_id


if __name__ == "__main__":
    # lv = LiveStreamStatus("assets/video.db", False)
    # # get_live_stream
    # # asyncio.run(lv.get_live_stream("ShuunAruna"))
    # x = (lv.get_channel_tag("UCGo7fnmWfGQewxZVDmC3iJQ"))
    # print(x)

    # x= asyncio.run(lv.get_live_stream_info("crHb_En5PwM","UCGo7fnmWfGQewxZVDmC3iJQ"))
    dic = {"2024-11-29 00:00:00+0700":"2024-11-29 00:00:00+0700", "2024-11-28 00:00:00+0700":None}
    print(dic["2024-11-28 00:00:00+0700"])



