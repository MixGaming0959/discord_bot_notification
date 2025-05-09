import asyncio
from datetime import datetime, timedelta

from fetchData import LiveStreamStatus

from get_env import GetEnv 

env = GetEnv()

# ฟังก์ชันสำหรับอัปเดตข้อมูลการสตรีม
async def update_live_table():
    ISUPDATE_PATH = env.get_env_str('ISUPDATE_PATH')
    live = LiveStreamStatus(env.get_env_bool('AUTO_CHECK'))

    date_format = "%Y-%m-%d %H:%M:%S%z"
    while True:
        time_now = live.db.datetime_gmt(datetime.now())

        current_time = datetime.strptime(
            time_now.strftime(date_format), date_format
        )

        with open(ISUPDATE_PATH, "r") as file: 
            update_time = datetime.strptime(
                file.read(), date_format
            ).replace(hour=0, minute=0, second=0)

        if current_time > update_time:
            print("Start update LiveTable...")
            listVtuber = live.db.listVtuberByGroup("PixelaProject")
            for _, v in enumerate(listVtuber):
                # live.set_channel_id(v["channel_id"])
                _, err = await live.live_stream_status(v["channel_id"])
                if err != None:
                    print(err)
                    break
            
        next_update = time_now.replace(hour=0, minute=0, second=0) + timedelta(days=1)
        wait_time = (next_update - time_now).total_seconds()
        
        hours = int(wait_time//3600)
        minutes = int((wait_time%3600)//60)
        seconds = int(wait_time%60)
        
        with open(ISUPDATE_PATH, "w") as file:
            file.write(next_update.strftime(date_format))
        print(f"Next check in {hours} hours {minutes} minutes {seconds} seconds...")
        await (asyncio.sleep(wait_time))

asyncio.run(update_live_table())

# if __name__ == "__main__":
