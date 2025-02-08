from get_env import GetEnv
from botDiscord import run_discord_bot
from receive_webhook import run_server
from botSendMessage import BotSendMessage
from subscribe_to_channel import SubscribeToChannel

# Main threading setup
import threading
import time
import subprocess
import logging
import os

# ตั้งค่าการบันทึก Log
LOG_DIR = "Log"
os.makedirs(LOG_DIR, exist_ok=True)  # สร้างโฟลเดอร์ Log ถ้ายังไม่มี
os.makedirs(os.path.join(LOG_DIR, time.strftime("%Y-%m-%d")), exist_ok=True)

date = time.strftime("%Y-%m-%d")
LOG_FILE = os.path.join(LOG_DIR, f"{date}/thread_monitor.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def monitor_threads(threads):
    """ตรวจสอบว่าเธรดยังทำงานอยู่หรือไม่"""
    while True:
        for thread in threads:
            if not thread.is_alive():
                error_msg = f"Thread {thread.name} died. Restarting script..."
                print(error_msg)
                logging.error(error_msg)
                
                # รีรันสคริปต์ใหม่
                subprocess.run(["python", "main.py"])
                return
        time.sleep(1)

if __name__ == "__main__":
    try:
        env = GetEnv()
        sub = SubscribeToChannel()
        botSendMSG = BotSendMessage(env.discord_token_env())

        # Create threads
        discord_thread = threading.Thread(target=run_discord_bot, args=(env.discord_token_env(),), daemon=True, name="DiscordBot")
        auto_check_db = threading.Thread(target=botSendMSG.run_send_message, daemon=True, name="AutoCheckDB")
        flask_thread = threading.Thread(target=run_server, daemon=True, name="FlaskServer")

        # Start threads
        discord_thread.start()
        auto_check_db.start()
        flask_thread.start()

        logging.info("All main threads started successfully.")

        # wait 3 seconds before starting subscribe_to_channel
        time.sleep(3)
        subscribe_to_channel_thread = threading.Thread(target=sub.run_subscribe_to_channel, daemon=True, name="SubscribeToChannel")
        subscribe_to_channel_thread.start()

        logging.info("SubscribeToChannel thread started successfully.")

        # รอให้ทุกเธรดเริ่มทำงานก่อน 5 วินาที
        time.sleep(5)

        # Monitor threads
        monitor_threads([discord_thread, auto_check_db, flask_thread])

    except Exception as e:
        error_msg = f"Fatal error: {e}"
        print(error_msg)
        logging.critical(error_msg)
