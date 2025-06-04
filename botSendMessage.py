from random import randint
import asyncio

from get_env import GetEnv
from database import DatabaseManager
from fetchData import LiveStreamStatus
from send_embed import DiscordSendData

def random_color():
    # Generate a random color as an integer value
    return int(randint(0, 0xFFFFFF))


class BotSendMessage:
    def __init__(self, discord_token: str):
        env = GetEnv()

        self.YOUTUBE_API_KEY = env.youtube_api_key_env()
        self.DISCORD_BOT_TOKEN = discord_token
        self.BEFORE_LIVE = env.get_env_int('BEFORE_LIVE')
        self.PUBSUBHUBBUB_URL = env.get_env_str("PUBSUBHUBBUB_URL")
        self.PROCESSED_PAYLOADS = list()
        self.LIMIT_TIME_LIFE = 20 # Seconds
        self.SEND_MSG_WHEN_START = env.get_env_bool('SEND_MSG_WHEN_START')
        # Database

        self.db = DatabaseManager()
        self.AUTO_CHECK = env.get_env_int('AUTO_CHECK')
        self.ISUPDATE_PATH = env.get_env_str('ISUPDATE_PATH')
        self.MAX_EMBED_SIZE = 4000

        self.liveStreamStatus = LiveStreamStatus(self.AUTO_CHECK)
        self.sendData = DiscordSendData(discord_token, self.db)

    async def get_live_videos(self):
        result = await (self.liveStreamStatus.get_before_live_stream())
        vtuber_id = set()
        gen_id = set()
        group_id = set()
        for r in result:
            vtuber_id = set()
            gen_id = set()
            group_id = set()
            vtuber = self.db.getVtuber(r["channel_id"])
            if vtuber is None:
                r['is_noti'] = True
                self.db.updateLiveTable(r)
                # print(f"BotSendMSG: Cannot get vtuber info: {r['channel_id']}")
                continue
            vtuber_id.add(vtuber["id"])
            gen_id.add(vtuber["gen_id"])
            group_id.add(vtuber["group_id"])
            if r['colaborator'] != None:
                colab = r['colaborator'].split(",")
                for c in colab:
                    vtuber_tmp = self.db.getVtuber(c.split(" ")[0])
                    if vtuber_tmp == None:
                        continue
                    # print(f"BotSendMSG: Cannot get vtuber info: {vtuber_tmp}")
                    vtuber_id.add(vtuber_tmp["id"])
                    gen_id.add(vtuber_tmp["gen_id"])
                    group_id.add(vtuber_tmp["group_id"])
            discord_details = self.db.getDiscordDetails(list(vtuber_id), list(gen_id), list(group_id))
            if len(discord_details) != 0:
                for d in set(tuple(d.items()) for d in discord_details):
                    dic = dict(d)
                    if dic["is_PreAlertEnabled"] == 0:
                        continue
                    self.sendData.send_embed(dic["channel_id"], [r], "before")

            r['is_noti'] = True
            self.db.updateLiveTable(r)

            print(f"BotSendMSG: Send Embed Complete")

        return "OK", 200

    async def run_send_message(self):
        print("BotSendMSG: Start Loop")
        # sys.stdout.flush()  # Force flush after print
        while True:
            try:
                await self.get_live_videos()
                await asyncio.sleep(1)
            except Exception as e:
                print(f"An error occurred: {e}")
                # sys.stdout.flush()  # Force flush after print
                await asyncio.sleep(1)


if __name__ == "__main__":
    env = GetEnv()
    # sub = SubscribeToChannel()
    botSendMSG = BotSendMessage(env.discord_token_env())

    asyncio.run(botSendMSG.run_send_message())