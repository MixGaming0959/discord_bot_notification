# importing os module 
# import os 

# os.system('start cmd /k "python subscribe_to_channel.py"')
# os.system('start cmd /k "python botDiscord.py"')
# os.system('start cmd /k "python flask_app.py"')
# os.system('start cmd /k "python botSendMessage.py"')

import time
from botDiscord import run_discord_bot
from flask_app import run_server
from botSendMessage import run_send_message
from subscribe_to_channel import run_subscribe_to_channel

import threading

# Main threading setup
if __name__ == "__main__":
    # Create threads for each function
    discord_thread = threading.Thread(target=run_discord_bot, daemon=True)
    auto_check_db = threading.Thread(target=run_send_message, daemon=True)
    flask_thread = threading.Thread(target=run_server, daemon=True)

    # Start threads
    discord_thread.start()
    auto_check_db.start()
    flask_thread.start()

    # wait 3 seconds before starting subscribe_to_channel
    time.sleep(3)
    subscribe_to_channel_thread = threading.Thread(target=run_subscribe_to_channel, daemon=True)
    subscribe_to_channel_thread.start()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")