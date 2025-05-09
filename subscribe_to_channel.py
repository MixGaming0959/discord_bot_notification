import asyncio
import requests # type: ignore
from database import DatabaseManager 

from get_env import GetEnv  # type: ignore

class SubscribeToChannel:
    def __init__(self):
        env = GetEnv()
        self.env = env

        db = DatabaseManager()
        subscribe = env.get_env_str("SUBSCRIBE_ONLY")
        listSubscribe = []
        listSubscribe = subscribe.split(",")
        self.CHANNEL_IDS = []
        for s in listSubscribe:
            for v in db.listVtuberByGroup(s):
                self.CHANNEL_IDS.append({"channel_id": v["channel_id"], "channel_tag": v["channel_tag"]})

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

    def run_subscribe_to_channel(self):
        while True:
            try:
                self.WEBHOOK_URL = self.env.webhook_url_env()
                with open(self.OLD_WEBHOOK_PATH, "r") as file: 
                    old_webhook = file.read()
                    if old_webhook != self.WEBHOOK_URL:
                        for channel_id in self.CHANNEL_IDS:
                            self.subscribe_to_channel(channel_id, old_webhook, "unsubscribe")
                        for v in self.CHANNEL_IDS:
                            # print(v)
                            self.subscribe_to_channel(v, self.WEBHOOK_URL, "subscribe")

                with open(self.OLD_WEBHOOK_PATH, "w") as file:
                    file.write(self.WEBHOOK_URL)
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                asyncio.run(asyncio.sleep(1))

        print("Run subscribe_to_channel Complete!!!")

if __name__ == "__main__":
    subscribe_to_channel = SubscribeToChannel()

    subscribe_to_channel.run_subscribe_to_channel()