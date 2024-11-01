from random import randint
import asyncio, traceback
from datetime import datetime, timedelta
import discord # type: ignore
from discord.ext import commands  # type: ignore
from database import DatabaseManager
from Encrypt import Encrypt
import fetchData

from dotenv import load_dotenv # type: ignore
load_dotenv()
from os import environ

def load_env_json(key:str):
    return environ.get(key)

# Setup
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='/', intents=intents, reconnect=True)

def random_color():
    # Generate a random color as an integer value
    return discord.Color(randint(0, 0xFFFFFF))
def str_to_bool(s:str) -> bool: 
    return s.lower() in ['true', '1', 'yes', 1, True]

de = Encrypt()
db_path = de.decrypt(load_env_json('DB_PATH'))
db = DatabaseManager(db_path)
AUTO_UPDATE = str_to_bool(load_env_json('AUTO_UPDATE'))
ISUPDATE_PATH = de.decrypt(load_env_json('ISUPDATE_PATH'))

liveStreamStatus = fetchData.LiveStreamStatus(db_path, AUTO_UPDATE)

def timeNowFunc():
    return liveStreamStatus.db.datetime_gmt(datetime.now())

TOKEN = de.decrypt(load_env_json('TOKEN'))

@client.event
async def on_ready():
    while True:
        try:
            print(f'Logged in as {client.user.name}')
            sync = await client.tree.sync()
            print(f'Synced {len(sync)} command(s)')
            # asyncio.create_task(bot_send_message_to_all_servers())
            break
        except Exception as e:
            print("Error: ", traceback.format_exc())
            await asyncio.sleep(10)

@client.event
async def on_disconnect():
    print('Bot disconnected from Discord!')

@client.event
async def on_error(event_method, *args, **kwargs):
    print(f'An error occurred: {event_method}, {args}, {kwargs}')

@client.tree.command(name='get-live', description="คำสั่งที่ดึงตารางไลฟ์ตามตัวเลือกที่คุณเลือก")
@discord.app_commands.choices(
    options = [
        discord.app_commands.Choice(name = "Vtuber", value = 0),
        discord.app_commands.Choice(name = "รุ่น/บ้าน", value = 1),
        discord.app_commands.Choice(name = "ค่าย", value = 2),
    ]
)
async def getLive(interaction, options: discord.app_commands.Choice[int], name: str, istoday: bool=True):
    await interaction.response.defer()
    listVtuber = []
    lis_embed = []
    try:
        # remove head and back white space
        name = name.strip()
        if options.value == 0:
            listVtuber = [db.getVtuber(name)]
        elif options.value == 1:
            listVtuber = db.listVtuberByGen(name)
        elif options.value == 2:
            listVtuber = db.listVtuberByGroup(name)
        else :
            embed = discord.Embed(
                title="ไม่พบข้อมูล",
                description=f"ไม่พบข้อมูล {name} ที่ต้องการ",
                color=discord.Color.yellow()
            )
            await interaction.followup.send(embeds=[embed])
            return
        
        if listVtuber == None or len(listVtuber) == 0 or listVtuber[0] == None:
            embed = discord.Embed(
                title="ไม่พบข้อมูล",
                description=f"ไม่พบข้อมูล {name} ที่ต้องการ",
                color=discord.Color.yellow()
            )
            await interaction.followup.send(embeds=[embed])
            return
        found = False
        for _, v in enumerate(listVtuber):
            if v == None or v["channel_id"] == None:
                continue
            liveStreamStatus.set_channel_id(v["channel_id"])
            live_streams = await liveStreamStatus.get_live_stream(v['channel_tag'])

            if len(live_streams) == 0:
                continue

            for stream in live_streams:
                # เช็ควันที่
                embedVtuber = discord.Embed(
                    title=v["name"],
                    description=f"ตารางไลฟ์ ประจำวันที่ {timeNowFunc().strftime('%d %B %Y')}",
                    color=random_color()
                )
                embedVtuber.set_thumbnail(url=v["image"])
                start_at = datetime.strptime(
                    stream['start_at'].strftime("%Y-%m-%d"), "%Y-%m-%d"
                )
                timeNow = datetime.strptime(
                    timeNowFunc().strftime("%Y-%m-%d"), "%Y-%m-%d"
                )
                # ตรวจสอบว่าในวันนี้มีไลฟ์หรือไม่
                if istoday and (start_at < timeNow) :
                    continue
                found = True
                embedVtuber.add_field(name='ชื่อไลฟ์', value=f"{stream['title']}\n[Link]({stream['url']})", inline=False)
                embedVtuber.add_field(name='สถานะ', value=stream['live_status'], inline=True)
                embedVtuber.add_field(name='เวลา', value=stream['start_at'].strftime("%d %B %Y %H.%M น."), inline=True)
                embedVtuber.set_image(url=stream['image'])
                # embedVtuber.set_footer(text=f"Tag: {v['channel_tag']}")
                lis_embed.append(embedVtuber)
        if options.value == 0 and not found:
            embed = discord.Embed(
                title=listVtuber[0]["name"],
                description=f"ตอนนี้ {listVtuber[0]['channel_tag']} ยังไม่มีตารางไลฟ์",
                color=discord.Color.yellow()
            )
            await interaction.followup.send(embeds=[embed])
            return

    except Exception as e:
        print("Error: ", traceback.format_exc())
        await interaction.followup.send(f"Error: {e}")
        return
    if len(lis_embed) == 0:
        embed = discord.Embed(
            title=name,
            description=f"ตอนนี้ {name} ยังไม่มีตารางไลฟ์",
            color=discord.Color.yellow()
        )
        await interaction.followup.send(embeds=[embed])
        return
    
    for i in range(len(lis_embed)):
        lis_embed[i].set_footer(text=f"Page: {i+1}/{len(lis_embed)}")
    # Create the paginator view
    paginator = Paginator(embeds=lis_embed)

    # Send the first embed
    message = await interaction.followup.send(embed=lis_embed[0], view=paginator)
    paginator.message = message  # Store the message for later access

@client.tree.command(name='get-live-table', description="คำสั่งที่ดึงตารางไลฟ์ตามตัวเลือกที่คุณเลือก")
async def getLiveTable(interaction: discord.Interaction, group_name: str):
    await interaction.response.defer()
    listVtuber = []
    listEmbed = []
    try:
        group_name = group_name.strip()
        data_gen = db.listGenByGroup(group_name)
        if data_gen == None or len(data_gen) == 0:
            embed = discord.Embed(
                title="ไม่พบข้อมูล",
                description=f"ไม่พบข้อมูล {group_name} ที่ต้องการ",
                color=discord.Color.yellow()
            )
            await interaction.followup.send(embeds=[embed], ephemeral=True)
            return
        pageInfo = 0
        for _, g in enumerate(data_gen):
            pageInfo+=1
            gen_name = g["name"]
            embedVtuber = discord.Embed(
                        title=f"ตารางไลฟ์ ประจำวันที่ {timeNowFunc().strftime('%d %B %Y')} ของ {gen_name}",
                        color=random_color(),
                    )
            embedVtuber.set_footer(text=f"Pages: {pageInfo}/{len(data_gen)}")
            embedVtuber.set_thumbnail(url=g['image'])
            listVtuber = db.listVtuberByGen(gen_name)
            if listVtuber == None or len(listVtuber) == 0 or listVtuber[0] == None:
                embedVtuber.add_field(name=f"ไม่มี Vtuber ใน Gen {gen_name} นี้", value="ไม่พบข้อมูล", inline=False)
                continue
            found = False
            for _, v in enumerate(listVtuber):
                # print(f"Gen: {gen_name}, Vtuber: {v['Name']}")
                live_streams = await liveStreamStatus.get_live_stream(v['channel_tag'])
                if live_streams == None or len(live_streams) == 0:
                    continue

                for stream in live_streams:
                    # เช็ควันที่
                    start_at = datetime.strptime(
                        stream['start_at'].strftime("%Y-%m-%d"), "%Y-%m-%d"
                    )
                    timeNow = datetime.strptime(
                        timeNowFunc().strftime("%Y-%m-%d"), "%Y-%m-%d"
                    )
                    if (start_at != timeNow) :
                        continue

                    txt = f"{stream['title']}\n [Link]({stream['url']})\n"
                    embedVtuber.add_field(name=v["name"], value=txt, inline=False)
                    embedVtuber.add_field(name='เวลาไลฟ์', value=f"{stream['start_at'].strftime('%H:%M')} น.", inline=True)
                    embedVtuber.add_field(name='สถานะ', value=f"{stream['live_status']}", inline=True)
                    found = True
            if not found:
                embedVtuber.add_field(name=f"ไม่พบไลฟ์ของ {gen_name} บน Youtube", value="ไม่พบไลฟ์บน Youtube", inline=False)

            listEmbed.append(embedVtuber)

    except Exception as e:
        print(traceback.format_exc())
        await interaction.followup.send(f"เกิดข้อผิดพลาด: {e}", ephemeral=True)
        return

    # Create the paginator view
    paginator = Paginator(embeds=listEmbed)

    # Send the first embed
    message = await interaction.followup.send(embed=listEmbed[0], view=paginator, ephemeral=True)
    paginator.message = message  # Store the message for later access


@client.tree.command(name='update-live', description="คำสั่งที่อัพเดทข้อมูลตารางเผื่อว่ามีไลฟ์ที่มีการเปลี่ยนแปลง")
@discord.app_commands.choices(
    options = [
        discord.app_commands.Choice(name = "Vtuber", value = 0),
        # discord.app_commands.Choice(name = "รุ่น/บ้าน", value = 1),
        # discord.app_commands.Choice(name = "ค่าย", value = 2),
    ]
)
async def updateLive(interaction: discord.Interaction, options: discord.app_commands.Choice[int], name: str):
    await interaction.response.defer()
   
    listVtuber = []
    try:
        name = name.strip()
        if options.value == 0:
            listVtuber = [db.getVtuber(name)]
        elif options.value == 1:
            listVtuber = db.listVtuberByGen(name)
        elif options.value == 2:
            listVtuber = db.listVtuberByGroup(name)
            date_format = "%Y-%m-%d %H:%M:%S%z"
            
            time_now = liveStreamStatus.db.datetime_gmt(datetime.now())

            current_time = datetime.strptime(
                time_now.strftime(date_format), date_format
            ).replace(hour=0, minute=0, second=0)

            with open(ISUPDATE_PATH, "r") as file: 
                update_time = datetime.strptime(
                    file.read(), date_format
                ).replace(hour=0, minute=0, second=0)

            if not(current_time > update_time) and AUTO_UPDATE:
                await interaction.followup.send(f"จะอัพเดทได้ในเวลา {update_time.strftime('%d %B %Y %H:%M')} น.")
                return
            else:
                next_update = time_now.replace(hour=9, minute=0, second=0) + timedelta(days=1)
                with open(ISUPDATE_PATH, "w") as file:
                    file.write(next_update.strftime(date_format))

        if listVtuber == None or len(listVtuber) == 0 or listVtuber[0] == None:
            await interaction.followup.send(f"ไม่พบข้อมูล {name} ในฐานข้อมูล!")
            return
            

        for _, v in enumerate(listVtuber):
            liveStreamStatus.set_channel_id(v['channel_id'])
            await liveStreamStatus.live_stream_status()

        await interaction.followup.send(f"อัพเดทข้อมูลตาราง {name} สําเร็จ...")
    except Exception as e:
        print(traceback.format_exc())
        await interaction.followup.send(f"เกิดข้อผิดพลาด: {e}")

@client.tree.command(name='check-live-status', description="ตรวจสอบสถานะไลฟ์ของ Vtuber ที่คุณเลือก")
@discord.app_commands.choices(
    options = [
        discord.app_commands.Choice(name = "Vtuber", value = 0),
        # discord.app_commands.Choice(name = "รุ่น/บ้าน", value = 1),
        # discord.app_commands.Choice(name = "ค่าย", value = 2),
    ]
)
async def checkLiveStatus(interaction: discord.Interaction, options: discord.app_commands.Choice[int], name: str):
    await interaction.response.defer()
   
    listVtuber = []
    try:
        name = name.strip()
        if options.value == 0:
            listVtuber = [db.getVtuber(name)]
        elif options.value == 1:
            listVtuber = db.listVtuberByGen(name)
        else:
            listVtuber = db.listVtuberByGroup(name)
        if listVtuber == None or len(listVtuber) == 0 or listVtuber[0] == None:
            await interaction.followup.send(f"ไม่พบข้อมูล {name} ในฐานข้อมูล!")
            return

        for _, v in enumerate(listVtuber):
            msg = await liveStreamStatus.check_live_status(v['channel_tag'])

        await interaction.followup.send(msg)
    except Exception as e:
        print(traceback.format_exc())
        await interaction.followup.send(f"เกิดข้อผิดพลาด: {e}")

class Paginator(discord.ui.View):
    def __init__(self, embeds, timeout=10):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0  # Start at the first page
        self.update_button_states()  # Initial state update

    # Update button states based on the current page
    def update_button_states(self):
        self.children[0].disabled = self.current_page == 0  # Disable Previous if on the first page
        self.children[1].disabled = self.current_page == 0  # Disable Previous if on the first page
        self.children[2].disabled = self.current_page == len(self.embeds) - 1  # Disable Next if on the last page
        self.children[3].disabled = self.current_page == len(self.embeds) - 1  # Disable Next if on the last page

    @discord.ui.button(label="First", style=discord.ButtonStyle.green)
    async def first_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page = 0
            self.update_button_states()  # Update button states
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    # Define the button for the previous page
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_button_states()  # Update button states
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    # Define the button for the next page
    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self.update_button_states()  # Update button states
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="Last", style=discord.ButtonStyle.primary)
    async def last_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page = len(self.embeds) - 1
            self.update_button_states()  # Update button states
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    async def on_timeout(self):
        # print("Timeout occurred: disabling buttons.")  # Log the timeout
        for item in self.children:
            item.disabled = True  # Disable all buttons
        await self.message.edit(view=self)  # Edit the message to update the view

@client.tree.command(name='test', description="สำหรับ Test เท่านั้น")
async def test(interaction: discord.Interaction, group_name: str):
    await interaction.response.defer()
    
    await interaction.followup.send(f"สำหรับ Test เท่านั้น")
    return



client.run(TOKEN)