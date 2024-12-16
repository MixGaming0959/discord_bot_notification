import asyncio
import textwrap
from datetime import datetime, timezone, timedelta
import textwrap
from database import DatabaseManager
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore
from get_env import GetEnv  # type: ignore


class LiveStreamStatus:
    def __init__(self, db_path: str, autoCheck: bool = False):
        self.db = DatabaseManager(db_path)
        self.autoCheck = autoCheck

        env = GetEnv()

        self.api_key = env.youtube_api_key_env()
        self.TIME_ERROR = timedelta(minutes=30)
        self.LIMIT_TRUNCATE_STRING = 100

    async def get_live_stream_info(self, video_ids: str, channel_id: str):
        vtuber = self.db.getVtuber(channel_id)
        try:
            youtube = build("youtube", "v3", developerKey=self.api_key)

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
        video_in_db = {}
        for v in self.db.getLiveTablebyURL(lis_video_id):
            video_in_db[v['url']] = v

        if "items" in response and response["items"]:
            for item in response["items"]:
                snippet = item["snippet"]
                live_status = snippet["liveBroadcastContent"]
                video_id = item["id"]
                title = snippet["title"]
                url = f"https://www.youtube.com/watch?v={video_id}"
                # print(video_in_db[url])
                # title contains "Birthday"
                if live_status == "none" and "Birthday" not in title:
                    # print(f"Channel {channel_tag} Url: {url} is not live")
                    lis_video_id.remove(video_id)
                    self.db.cancelLiveTable(
                        url, "end"
                    )
                    continue

                video_status = item["status"]
                privacy_status = video_status.get("privacyStatus", "unknown")

                # ตรวจสอบว่าสถานะเป็นส่วนตัวหรือไม่
                if privacy_status == "private":
                    self.db.cancelLiveTable(
                        url, "private"
                    )
                elif privacy_status == "public":
                    pass
                elif privacy_status == "unlisted":
                    pass
                else:
                    self.db.cancelLiveTable(
                        url, "unknown"
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
                    
                colaborator = self.set_collaborator(title=title)

                data = {
                    "title": title,
                    "url": url,
                    "start_at": None,
                    "colaborator": colaborator,
                    "vtuber_id": vtuber["id"],
                    "image": image,
                    "live_status": live_status,
                    "channel_name": channel_name,
                    "channel_tag": vtuber["channel_tag"],
                    "channel_id": channel_id,
                    "is_noti": video_in_db[url]["is_noti"] if url in video_in_db else False,
                }

                # ตรวจสอบเวลาเริ่มและสถานะการถ่ายทอดสด
                live_details = item["liveStreamingDetails"] if "liveStreamingDetails" in item else ""
                if "actualStartTime" in live_details:
                    # ถ้าเริ่มถ่ายทอดสดแล้ว แปลงเวลาที่เริ่มเป็น datetime object
                    start_at = datetime.fromisoformat(
                        live_details["actualStartTime"][:-1]
                    ).replace(tzinfo=timezone.utc)
                    data["start_at"] = self.db.datetime_gmt(start_at)
                    # current_time = datetime.now(timezone.utc)
                    # elapsed_time = current_time - actual_start_time
                    # print(f"Live started {elapsed_time.total_seconds() // 60} minutes ago.")
                    # print("Live started:", data["start_at"])

                elif "scheduledStartTime" in live_details:
                    # ถ้ายังไม่เริ่มถ่ายทอดสด ดูเวลาที่ตั้งไว้สำหรับเริ่ม
                    start_at = datetime.fromisoformat(
                        live_details["scheduledStartTime"][:-1]
                    ).replace(tzinfo=timezone.utc)
                    data["start_at"] = self.db.datetime_gmt(start_at)
                    # print("Live scheduled to start 1:", data["start_at"])
                else:
                    # now
                    start_at = self.db.datetime_gmt(datetime.now())
                    data["start_at"] = start_at
                    # print("Live scheduled to start 2:", data["start_at"])


                if url in video_in_db:
                    if (data["title"] != video_in_db[url]["title"]
                    or data["image"] != video_in_db[url]["image"]
                    or data["start_at"] != video_in_db[url]["start_at"]
                    or data["live_status"] != video_in_db[url]["live_status"]):
                        data["is_noti"] = False

                lis_video_id.remove(video_id)
                result.append(data)

        if len(lis_video_id) != 0 and lis_video_id[0] != "":
            for video_id in lis_video_id:
                self.db.cancelLiveTable(
                    f"https://www.youtube.com/watch?v={video_id}", "cancelled"
                )
            print(vtuber["name"], f"https://www.youtube.com/watch?v={video_id}", "cancelled")
       
        return result
    
    def set_collaborator(self, title: str):
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
        return colaborator

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
            data["start_at"] = self.truncate_date(dt.strftime("%Y-%m-%d %H:%M:%S%z"), "%Y-%m-%d %H:%M:%S%z")
            found = False
            for i in time_list:
                if data["start_at"] - self.TIME_ERROR <= i <= data["start_at"] + self.TIME_ERROR and data['colaborator'] != None:
                    found = True
                    break
            if found:
                continue
            time_list.add(data["start_at"])
            old_start_at = data["start_at"]
            isUpcoming = data["live_status"] in ["upcoming", "live"] and data["start_at"] < self.db.datetime_gmt(datetime.now())
            if self.autoCheck and isUpcoming:
                video_id = data["url"].replace("https://www.youtube.com/watch?v=", "")
                video_details = await self.get_live_stream_info(video_id, data["channel_id"])
                if video_details == None or len(video_details) == 0:
                    continue
                video_details = video_details[0]
                # print("1 is_noti", data['is_noti'], video_details['is_noti'])
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
                # print("2 is_noti", data['is_noti'], video_details['is_noti'])
                video_details = data
            if old_start_at != video_details["start_at"]:
                print("Update", data["title"], video_details["live_status"])
                continue
            video_details['title'] = self.truncate_string(video_details['title'], self.LIMIT_TRUNCATE_STRING)
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
            data["start_at"] = self.truncate_date(dt.strftime("%Y-%m-%d %H:%M:%S%z"), "%Y-%m-%d %H:%M:%S%z")
            timeNow = datetime.strptime(
                self.db.datetime_gmt(datetime.now()).strftime("%Y-%m-%d"), "%Y-%m-%d"
            )

            found = False
            for i in time_list:
                if data["start_at"] - self.TIME_ERROR <= i <= data["start_at"] + self.TIME_ERROR:
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
        youtube = build("youtube", "v3", developerKey=self.api_key)

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
        youtube = build('youtube', 'v3', developerKey=self.api_key)

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
            # playlist_id = self.get_channel_info(channel_id)
            # if playlist_id == None:
            #     raise ValueError("Cannot get channel info")
            playlist_id = "UU" + channel_id[2:]

            lis_video_id = self.get_playlist_item(playlist_id, channel_id)
            if lis_video_id == None:
                raise ValueError("Cannot get playlist item")
            
            if len(lis_video_id) == 0:
                return None, None

            video_details = await self.get_live_stream_info(",".join(lis_video_id), channel_id)
            if video_details == None:
                raise ValueError("Cannot get live stream info")

            if len(video_details) == 0:
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
            youtube = build("youtube", "v3", developerKey=self.api_key)
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
            youtube = build("youtube", "v3", developerKey=self.api_key)
            request = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=playlist_id,
                maxResults=10
            )
            response = request.execute()
            # print(member_playlist)
            request_member = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=member_playlist,
                maxResults=5
            )
            try:
                response_member = request_member.execute()
                # googleapiclient.errors.HttpError: <HttpError 404 when requesting https://youtube.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId=UUMOcRaKGCG3RFenb8D2php_Jw&maxResults=5&key=AIzaSyABUXA9Feul73lQRgpytUV1OdsG2GzmtLM&alt=json returned "The playlist identified with the request's <code>playlistId</code> parameter cannot be found.". Details: "[{'message': "The playlist identified with the request's <code>playlistId</code> parameter cannot be found.", 'domain': 'youtube.playlistItem', 'reason': 'playlistNotFound', 'location': 'playlistId', 'locationType': 'parameter'}]">
            except HttpError as e:
                if e.error_details[0]["reason"] == "playlistNotFound":
                    response_member = {"items": []}
                else:
                    raise e
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
                publishedAt = self.db.datetime_gmt(self.truncate_date(detail["videoPublishedAt"], "%Y-%m-%dT%H:%M:%SZ"))
                if not (publishedAt >= timeAfter and publishedAt <= timeBefore):
                    break
                video_id = str(detail["videoId"])
                result_video_id.append(video_id)

        if "items" in response_member and response_member["items"]:
            # print("member")
            for item in response_member["items"]:
                detail = item["contentDetails"] 
                    
                publishedAt = self.db.datetime_gmt(self.truncate_date(detail["videoPublishedAt"], "%Y-%m-%dT%H:%M:%SZ"))
                if not (publishedAt >= timeAfter and publishedAt <= timeBefore):
                    break
                video_id = str(detail["videoId"])
                result_video_id.append(video_id)

        return result_video_id

    async def get_before_live_stream(self):
        video = self.db.getLiveTable_30()

        # เก็บเวลาไลฟ์ แบบ list
        time_list = set()

        result = []
        # ตรวจสอบว่าเริ่มถ่ายทอดสดหรือยัง
        if video == None:
            # print("No data")
            return result
        
        for data in video:
            video_details = {}
            dt = datetime.fromisoformat(data["start_at"])
            data["start_at"] = self.truncate_date(dt.strftime("%Y-%m-%d %H:%M:%S%z"), "%Y-%m-%d %H:%M:%S%z")
            # print(data["is_noti"])
            if data['is_noti'] == 1:
                continue

            time_list.add(data["start_at"])
            old_start_at = data["start_at"]
            isUpcoming = data["live_status"] in ["upcoming", "live"]
            if self.autoCheck and isUpcoming:
                video_id = data["url"].replace("https://www.youtube.com/watch?v=", "")
                video_details = await self.get_live_stream_info(video_id, data["channel_id"])
                if video_details == None or len(video_details) == 0:
                    continue

                video_details = video_details[0]
                video_details['is_noti'] = True

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
            new_start_at = video_details["start_at"]
            # เผื่อมีการอัพเดลเวลา
            # Before 19.00 - 30 = 18.30 < Now (18.30) < 19.00 + 10 = 19.10 :  pass
            # After  21.30 - 30 = 21.00 < Now (18.30) < 21.30 + 10 = 21.40 :  continue
            # After  19.30 - 30 = 19.00 < Now (18.30) < 19.30 + 10 = 19.40 :  continue
            print(old_start_at, new_start_at, data["live_status"], video_details["live_status"])
            if old_start_at != new_start_at or data["live_status"] != video_details["live_status"] or video_details["live_status"] == 'live':
                # print("Update", data["title"], video_details["live_status"], old_start_at, new_start_at)
                continue

            video_details['is_noti'] = True
            self.db.updateLiveTable(video_details)

            video_details['title'] = self.truncate_string(video_details['title'], self.LIMIT_TRUNCATE_STRING)
            result.append(video_details)

        return result
    
    def truncate_date(self, date_str: str, date_format="%Y-%m-%dT%H:%M:%S%z") -> datetime:
        if "." in date_str:
            reversed_date_str = date_str[::-1]
            if "+" in reversed_date_str:
                reversed_date_str = reversed_date_str[:reversed_date_str.index("+")+1]
            else:
                reversed_date_str = reversed_date_str[:reversed_date_str.index("-")+1]
            date_str = date_str[:date_str.index(".")] + reversed_date_str[::-1]

        return datetime.strptime(date_str, date_format)
if __name__ == "__main__":
    lv = LiveStreamStatus("assets/video.db", True)
    # # get_live_stream
    # # asyncio.run(lv.get_live_stream("ShuunAruna"))
    # x = (lv.get_channel_tag("UCGo7fnmWfGQewxZVDmC3iJQ"))
    # print(x)

    x = asyncio.run(lv.get_before_live_stream())
    for i in x:
        print(i['title'])

    


