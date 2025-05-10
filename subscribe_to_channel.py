import asyncio
import requests # type: ignore
from database import DatabaseManager 

from get_env import GetEnv  # type: ignore

class SubscribeToChannel:
    def __init__(self):
        env = GetEnv()
        self.env = env

        self.db = DatabaseManager()
        subscribe = env.get_env_str("SUBSCRIBE_ONLY")
        self.listSubscribe = subscribe.split(",")

        self.PUBSUBHUBBUB_URL = env.get_env_str("PUBSUBHUBBUB_URL")
        self.OLD_WEBHOOK_PATH = env.get_env_str("OLD_WEBHOOK_PATH")

    def subscribe_to_channel(self, channel_details, callback_url, subscribe):
        """Subscribe to a YouTube channel's feed."""
        channel_id = channel_details["channel_id"]
        channel_tag = channel_details["channel_tag"]
        topic_url = f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel_id}"
        data = {
            "hub.callback": callback_url,
            "hub.topic": topic_url,
            "hub.mode": subscribe,
            "hub.verify": "async",
        }
        
        try:
            response = requests.post(self.PUBSUBHUBBUB_URL, data=data)
            if response.status_code != 202:
                print(f"Failed to subscribe to channel {channel_tag}. Response: {response.text}")
            else:
                print(f"{subscribe} request accepted for channel {channel_tag}: {channel_id}.")
        except Exception as e:
            print(f"An error occurred: {e}")

    async def run_subscribe_to_channel(self):
        print("SubscribeToChannel: Start Loop")
        while True:
            try:
                self.WEBHOOK_URL = self.env.webhook_url_env()

                channel_ids = []
                for s in self.listSubscribe:
                    list_vtuber = self.db.listVtuberByGroup(s, False)
                    if list_vtuber is None:
                        continue
                    for v in list_vtuber:
                        print(f"Channel Tag: {v['channel_tag']}")
                        channel_ids.append({"channel_id": v["channel_id"], "channel_tag": v["channel_tag"]})

                for channel in channel_ids:
                    self.subscribe_to_channel(channel, self.WEBHOOK_URL, "subscribe")
                    self.db.update_subscribe_notify(channel["channel_id"], True)

                # asyncio.sleep(60)
                await asyncio.sleep(60)
            except Exception as e:
                print(f"An error occurred: {e}")
                # asyncio.sleep(1)
                await asyncio.sleep(1)

if __name__ == "__main__":
    subscribe_to_channel = SubscribeToChannel()

    asyncio.run(subscribe_to_channel.run_subscribe_to_channel())