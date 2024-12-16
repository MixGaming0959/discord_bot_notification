from dotenv import load_dotenv # type: ignore
from Encrypt import Encrypt
from os import environ

load_dotenv()
class GetEnv:
    def __init__(self):
        self.encrypy = Encrypt()

    def get_env_str(self, key:str):
        return environ.get(key)
    
    def get_env_int(self, key:str):
        return int(environ.get(key))
    
    def get_env_bool(self, key:str):
        return (environ.get(key)).lower() in ['true', '1', 'yes', 1, True]
    
    def discord_token_env(self):
        return self.encrypy.decrypt(environ.get("DISCORD_BOT_TOKEN"))

    def youtube_api_key_env(self):
        return self.encrypy.decrypt(environ.get("YOUTUBE_API_KEY"))
    
    def webhook_url_env(self):
        return environ.get("WEBHOOK_URL")
    
    def webhook_port_env(self):
        return int(environ.get("WEBHOOK_PORT"))
    