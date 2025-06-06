import textwrap
from datetime import datetime, timezone, timedelta
import textwrap
from database import DatabaseManager
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore

from google.auth.transport.requests import Request # type: ignore
from google.oauth2.credentials import Credentials # type: ignore
from google_auth_oauthlib.flow import InstalledAppFlow # type: ignore

from get_env import GetEnv  # type: ignore

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

class LiveStreamStatus:
    def __init__(self, autoCheck: bool = False):
        self.db = DatabaseManager()
        self.autoCheck = autoCheck

        env = GetEnv()

        self.api_key = env.youtube_api_key_env()
        self.TIME_ERROR = timedelta(minutes=30)
        self.LIMIT_TRUNCATE_STRING = 100
        self.USE_API_KEY = env.get_env_bool('USE_API_KEY')
        self.gmt = env.get_env_int("GMT")

    def get_youtube_service(self):
        if self.USE_API_KEY:
            return build("youtube", "v3", developerKey=self.api_key)

        path_google = 'assets/google_assets/'
        creds = None
        # ลองโหลด token ที่เคยบันทึกไว้
        try:
            creds = Credentials.from_authorized_user_file(path_google+"token.json", SCOPES)
        except Exception:
            pass  # ถ้าไม่มีไฟล์ token.json ให้ข้ามไป

        # ถ้าไม่มี Credentials หรือหมดอายุ ให้รัน OAuth Flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())  # รีเฟรชโทเค็นถ้าหมดอายุ
            else:
                flow = InstalledAppFlow.from_client_secrets_file(path_google+"client_secret.json", SCOPES)
                creds = flow.run_local_server(port=0)

            # บันทึก token ใหม่
            with open(path_google+"token.json", "w") as token_file:
                token_file.write(creds.to_json())

        # สร้าง YouTube API Client
        return build("youtube", "v3", credentials=creds)

    def fetch_video_details(self, youtube, video_ids:str, part="liveStreamingDetails,snippet,status"):
        results = []
        batch_size = 40  # YouTube API limit
        list_ids = video_ids.split(",")
        for i in range(0, len(list_ids), batch_size):
            batch = list_ids[i:i+batch_size]
            request = youtube.videos().list(
                part=part,
                id=",".join(batch)
            )
            response = request.execute()
            results.extend(response.get("items", []))
        
        return results

    async def get_live_stream_info(self, video_ids: str, channel_id: str):
        vtuber = self.db.getVtuber(channel_id)
        try:
            youtube = self.get_youtube_service()
            response = self.fetch_video_details(youtube, video_ids)

        except Exception as e:
            video_in_db = []
            lis_video_id = video_ids.split(",")
            if len(lis_video_id) == 1:
                for video_id in lis_video_id:
                    self.db.cancelLiveTable(
                        f"https://www.youtube.com/watch?v={video_id}", "cancelled"
                    )
                    video_in_db.append(self.db.getLiveTablebyURL(lis_video_id))

                return video_in_db
                
            print(e)
            return None
        
        result = []
        lis_video_id = video_ids.split(",")
        video_in_db = {}
        for v in self.db.getLiveTablebyURL(lis_video_id):
            video_in_db[v['url']] = v

        if len(response) > 0:
            for item in response:
                snippet = item["snippet"]
                live_status = snippet["liveBroadcastContent"]
                video_id = item["id"]
                title = snippet["title"]
                url = f"https://www.youtube.com/watch?v={video_id}"
                # print(video_in_db[url])
                # title contains "Birthday"
                if live_status == "none":
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
                    "channel_title": snippet["channelTitle"],
                    "channel_tag": vtuber["channel_tag"],
                    "channel_id": channel_id,
                    "is_noti": video_in_db[url]["is_noti"] if url in video_in_db else False,
                }

                # ตรวจสอบเวลาเริ่มและสถานะการถ่ายทอดสด
                live_details = item["liveStreamingDetails"] if "liveStreamingDetails" in item else ""
                if "actualStartTime" in live_details:
                    # ถ้าเริ่มถ่ายทอดสดแล้ว แปลงเวลาที่เริ่มเป็น datetime object
                    dt = datetime.strptime(live_details["actualStartTime"][:-1], "%Y-%m-%dT%H:%M:%S")
                    start_at = dt.replace(tzinfo=timezone.utc)
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
            lis_colab = []
            for i in tmp.split("@")[1:]:
                lis_colab.append(i.split(" ")[0])
            colaborator = ",".join(lis_colab)

        elif "ft." in title.lower():
            tmp = title.lower()
            tmp = title[tmp.strip().index("ft.") + 3 :]
            colaborator = ""
            for i in tmp.split(","):
                colab_name = i.split(" ")[0].strip()
                if colab_name == "":
                    continue
                vtuber = self.db.getVtuber(colab_name)
                if vtuber == None:
                    colaborator += f"{colab_name},"
                else:
                    colaborator += f"{vtuber['channel_tag']},"
            colaborator = colaborator[:-1]
        return colaborator

    def set_channel_id(self, channel_id: str):
        self.channel_id = channel_id

    async def get_live_stream(self, channel_tag: str, fetch_all: bool = False):
        video = self.db.getLiveTable(channel_tag)

        # เก็บเวลาไลฟ์ แบบ list
        time_list = set()

        # if fetch_all:
        #     list_video_id = [i["url"].replace("https://www.youtube.com/watch?v=", "") for i in video]
        #     await self.get_live_stream_info(video_id, data["channel_id"])


        result = []
        # ตรวจสอบว่าเริ่มถ่ายทอดสดหรือยัง
        if video == None:
            return result
        for data in video:
            video_details = {}
            # dt = datetime.fromisoformat(data["start_at"])
            dt = data["start_at"]
            dt = dt.replace(tzinfo=timezone.utc)  # or use another timezone
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
            if (self.autoCheck and isUpcoming) or fetch_all:
                video_id = data["url"].replace("https://www.youtube.com/watch?v=", "")
                video_details = await self.get_live_stream_info(video_id, data["channel_id"])
                if video_details == None or len(video_details) == 0:
                    continue
                video_details = video_details[0]
                
                ## Update ช่อง
                if (data['channel_name'] != video_details['channel_title']
                    or data['channel_tag'] != video_details['channel_tag']):
                    updated_data_channel = self.get_channel_details(video_details['channel_id'])
                    if updated_data_channel is not None:
                        print(f"Update Old {data['channel_name']} New {updated_data_channel['channel_name']}")
                        self.db.updateVtuber(data['channel_id'], updated_data_channel)
                        data['channel_name'] = updated_data_channel['channel_name']
                        data['channel_tag'] = updated_data_channel['channel_tag']

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
            dt = data["start_at"]
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

    def insert_channel(self, username: str, gen_name, group_name):
        channel = self.db.getVtuber(username)
        if channel != None:
            raise ValueError(f"ชื่อ {channel['name']} มีอยู่แล้วในฐานข้อมูล...")
        youtube = self.get_youtube_service()

        request = youtube.search().list(
            part="snippet",
            q=username,
            type="channel",
            maxResults=1,  # จำนวนผลลัพธ์ที่ต้องการ
        )

        response = request.execute()

        # แสดงผลชื่อและข้อมูลช่องที่ค้นหาได้
        target_similarity = {}
        for item in response["items"]:
            name = item["snippet"]["channelTitle"]
            target_similarity[name] = {"item": item}
        
        if len(target_similarity) == 0:
            raise ValueError(f"ไม่พบช่องที่เกี่ยวข้องกับ {username}")

        channel_target = self.db.simpleCheckSimilarity(list(target_similarity.keys()), username)
        for item in [target_similarity[channel_target]['item']]:
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

        raise ValueError(f"ไม่พบช่องที่เกี่ยวข้องกับ {username}")
    
    def get_channel_tag(self, channel_id:str):
        youtube = self.get_youtube_service()

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
                raise ValueError(f"Channel id: {channel_id} Cannot get playlist item")
            
            if len(lis_video_id) == 0:
                print("Cannot get live stream info")
                return None, None

            video_details = await self.get_live_stream_info(",".join(lis_video_id), channel_id)
            if video_details == None:
                raise ValueError(f"Channel id: {channel_id} Cannot get live stream info")

            if len(video_details) == 0:
                print("Cannot get live stream info")
                return None, None

            for data in video_details:
                self.db.checkLiveTable(data)

            return video_details, None
        except HttpError as e:
            error_reason = (
                e.error_details[0]["reason"] if e.error_details else "unknown error"
            )
            print("Channel id: ", channel_id)
            raise error_reason
        except Exception as e:
            print("Channel id: ", channel_id)
            raise e

    def get_channel_info(self, channel_id:str):
        try: 
            youtube = self.get_youtube_service()
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
            youtube = self.get_youtube_service()
            request = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=playlist_id,
                maxResults=50
            )
            try:
                response = request.execute()
            except HttpError as e:
                if e.error_details[0]["reason"] == "playlistNotFound":
                    response = {"items": []}
                else:
                    print(f"response Error: {e}")
                    raise e
            # print(member_playlist)
            request_member = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=member_playlist,
                maxResults=25
            )
            try:
                response_member = request_member.execute()
                # googleapiclient.errors.HttpError: <HttpError 404 when requesting https://youtube.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId=UUMOcRaKGCG3RFenb8D2php_Jw&maxResults=5&key=AIzaSyABUXA9Feul73lQRgpytUV1OdsG2GzmtLM&alt=json returned "The playlist identified with the request's <code>playlistId</code> parameter cannot be found.". Details: "[{'message': "The playlist identified with the request's <code>playlistId</code> parameter cannot be found.", 'domain': 'youtube.playlistItem', 'reason': 'playlistNotFound', 'location': 'playlistId', 'locationType': 'parameter'}]">
            except HttpError as e:
                if e.error_details[0]["reason"] == "playlistNotFound":
                    response_member = {"items": []}
                else:
                    print(f"response_member Error: {e}")
                    raise e
        except HttpError as e:
            error_reason = (
                e.error_details[0]["reason"] if e.error_details else "unknown error"
            )
            raise error_reason
        except Exception as e:
            raise e
        result_video_id = []
        timeBefore = self.db.datetime_gmt(datetime.now() + timedelta(days=30))
        timeAfter = self.db.datetime_gmt(datetime.now() - timedelta(days=30))
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
            return result
        
        for data in video:
            video_details = {}
            data["start_at"] = self.db.datetime_gmt(data["start_at"] - timedelta(hours=7))
            if data['is_noti'] == 1:
                continue

            time_list.add(data["start_at"])
            old_start_at = data["start_at"]
            isUpcoming = data["live_status"] in ["upcoming", "live"]
            if self.autoCheck and isUpcoming:
                video_id = data["url"].replace("https://www.youtube.com/watch?v=", "")
                video_details = await self.get_live_stream_info(video_id, data["channel_id"])
                if video_details == None or len(video_details) == 0:
                    # print("Cannot get live stream info")
                    continue

                video_details = video_details[0]
                video_details['is_noti'] = True

                # เช็คว่า Liveหรือยัง มีการเปลี่ยนคอนเทนต์หรือไม่
                # print(data["start_at"], video_details["start_at"])
                if (
                    data["title"] != video_details["title"]
                    or data["image"] != video_details["image"]
                    or data["start_at"] != video_details["start_at"]
                    or data["live_status"] != video_details["live_status"]):
                    # print("Update", data["title"], video_details["live_status"])
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
            # print(old_start_at != new_start_at, data["live_status"], video_details["live_status"])
            if old_start_at != new_start_at or data["live_status"] != video_details["live_status"] or video_details["live_status"] == 'live':
                # print("Update", data["title"], video_details["live_status"], old_start_at, new_start_at)
                continue

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

    def insert_channel_from_main_channel(self, channel_tag: str):
        try: 
            youtube = self.get_youtube_service()
            request = youtube.search().list(
                part="snippet",
                q=channel_tag,
                type="channel",
                maxResults=1,  # จำนวนผลลัพธ์ที่ต้องการ
            )

            response = request.execute()
            # ค้นหาช่องหลัก เช่น Pixela Project
            target_similarity = {}
            for item in response["items"]:
                name = item["snippet"]["channelTitle"]
                target_similarity[name] = {"item": item}

            if len(target_similarity) == 0:
                raise ValueError(f"ไม่พบช่องที่เกี่ยวข้องกับ {channel_tag}")

            # to [name1, name2, ...]
            channel_target = self.db.simpleCheckSimilarity(list(target_similarity.keys()), channel_tag)
            target_item = target_similarity[channel_target]["item"]
            group_name = target_item["snippet"]["channelTitle"]
            group_channel_id = target_item["snippet"]["channelId"]
            
            request = youtube.channelSections().list(
                part="snippet,contentDetails",
                channelId=group_channel_id
            )

            response = request.execute()
            group_channel = {
                "group_name": group_name,
                "details": []
            }
            for item in response["items"]:
                snippet = item["snippet"]
                if snippet['type'] == "multiplechannels":
                    gen_name = str(snippet['title'])
                    vtuber_in_gen = list(item["contentDetails"]["channels"])
                    group_channel['details'].append({
                        "gen_name": gen_name,
                        "vtuber_in_gen": vtuber_in_gen
                })
            if group_channel['details'] == []:
                raise ValueError(f"ช่อง {group_channel['group_name']} อาจจะยังไม่ได้มีการเพิ่ม Vtuber เข้าไป")
            
            result = []
            for de in group_channel['details']:
                channel_ids = ",".join(de['vtuber_in_gen'])
                gen_name = de['gen_name']
                request = youtube.channels().list(
                    part="snippet,contentDetails",
                    id=channel_ids,
                    maxResults=50
                )
                response = request.execute() 

                for item in response["items"]:
                    snippet = item["snippet"]
                    channel_name = str(snippet['title'])
                    channel_tag = str(snippet['customUrl']).replace("@", "")

                    thumbnails = item["snippet"]["thumbnails"]
                    image = thumbnails["default"]["url"]
                    if "maxres" in thumbnails:
                        image = thumbnails["maxres"]["url"]
                    elif "high" in thumbnails:
                        image = thumbnails["high"]["url"]
                    elif "medium" in thumbnails:
                        image = thumbnails["medium"]["url"]

                    data = {
                        "name": channel_name,
                        "gen_name": de['gen_name'],
                        "group_name": group_channel['group_name'],
                        "youtube_tag": channel_tag,
                        "image": image,
                        "channel_id": item['id'],
                    }
                    try:
                        self.db.insertVtuber(data)
                        result.append(data)
                    except Exception as e:
                        if "has already in database" in str(e):
                            continue
                        else:
                            raise e
            if len(result) == 0:
                raise ValueError(f"ไม่ได้มีการอัพเดต Vtuber คนใหม่")
            return result
        except Exception as e:
            print(e)
            raise e
        
    def get_channel_details(self, channel_id:str) -> dict | None:
        youtube = self.get_youtube_service()

        # ขอข้อมูล channel โดยใช้ part brandingSettings
        request = youtube.channels().list(
            part='snippet,brandingSettings',
            id=channel_id
        )

        response = request.execute()
        if "items" in response and response["items"]:
            item = response["items"][0]
            thumbnails = item["snippet"]["thumbnails"]
            image = thumbnails["default"]["url"]
            
            if "maxres" in thumbnails:
                image = thumbnails["maxres"]["url"]
            elif "high" in thumbnails:
                image = thumbnails["high"]["url"]
            elif "medium" in thumbnails:
                image = thumbnails["medium"]["url"]
            data = {
                "channel_name": item["snippet"]["title"],
                "channel_tag": item["snippet"]["customUrl"].replace("@", "").title(),
                "image": image,
                "channel_id": item['id'],
            }
            return data
        else:
            return None

if __name__ == "__main__":
    lv = LiveStreamStatus(True)

    x = lv.get_channel_details("UCkEcY4RbLYs2AF45nhkyjtw")
    print(x)


    


