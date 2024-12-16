# importing os module 
# import os 

# os.system('start cmd /k "python subscribe_to_channel.py"')
# os.system('start cmd /k "python botDiscord.py"')
# os.system('start cmd /k "python flask_app.py"')
# os.system('start cmd /k "python botSendMessage.py"')

import time
import threading

from get_env import GetEnv
from botDiscord import run_discord_bot
from flask_app import run_server
from botSendMessage import BotSendMessage
from subscribe_to_channel import SubscribeToChannel

# Main threading setup
if __name__ == "__main__":
    env = GetEnv()
    sub = SubscribeToChannel()
    botSendMSG = BotSendMessage(env.discord_token_env())
    # Create threads for each function
    discord_thread = threading.Thread(target=run_discord_bot, args=(env.discord_token_env(),), daemon=True)
    auto_check_db = threading.Thread(target=botSendMSG.run_send_message, daemon=True)
    flask_thread = threading.Thread(target=run_server, daemon=True)

    # Start threads
    discord_thread.start()
    auto_check_db.start()
    flask_thread.start()

    # wait 3 seconds before starting subscribe_to_channel
    time.sleep(3)
    subscribe_to_channel_thread = threading.Thread(target=sub.run_subscribe_to_channel, daemon=True)
    subscribe_to_channel_thread.start()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Error: {e}")