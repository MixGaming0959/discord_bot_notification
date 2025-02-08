from dotenv import load_dotenv # type: ignore
from Encrypt import Encrypt
from os import environ
import requests # type: ignore

load_dotenv()

AUTO_GET_NGROK_URL = environ.get("")

class GetEnv:
    def __init__(self):
        self.encrypy = Encrypt()

    def get_env_str(self, key:str) -> str:
        return environ.get(key)
    
    def get_env_int(self, key:str) -> int:
        return int(environ.get(key))
    
    def get_env_bool(self, key:str) -> bool:
        return (environ.get(key)).lower() in ['true', '1', 'yes', 1, True]
    
    def discord_token_env(self) -> str:
        return self.encrypy.decrypt(environ.get("DISCORD_BOT_TOKEN"))

    def youtube_api_key_env(self) -> str:
        return self.encrypy.decrypt(environ.get("YOUTUBE_API_KEY"))
    
    def webhook_url_env(self) -> str:
        url = environ.get("WEBHOOK_URL")
        AUTO_GET_NGROK_URL = self.get_env_bool('AUTO_GET_NGROK_URL')
        if AUTO_GET_NGROK_URL:
            # เรียก API ของ Ngrok
            response = requests.get("http://127.0.0.1:4040/api/tunnels")
            data = response.json()

            # ดึง URL ออกมา
            url = data['tunnels'][0]['public_url'] + "/api/v1/webhooks"

        return url
    
    def webhook_port_env(self) -> int:
        return int(environ.get("WEBHOOK_PORT"))
    