from random import randint
import asyncio, traceback
from datetime import datetime, timedelta
import discord # type: ignore
from discord import app_commands, Embed as discordEmbed # type: ignore
from discord.ui import button as discordButton, View as discordView # type: ignore
from discord.ext import commands  # type: ignore
from database import DatabaseManager
import fetchData

from get_env import GetEnv

env = GetEnv()

# Setup
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='/', intents=intents, reconnect=True)

def random_color():
    # Generate a random color as an integer value
    return discord.Color(randint(0, 0xFFFFFF))

db_path = env.get_env_str('DB_PATH')
db = DatabaseManager(db_path)
AUTO_CHECK = env.get_env_str('AUTO_CHECK')
ISUPDATE_PATH = env.get_env_str('ISUPDATE_PATH')
MAX_EMBED_SIZE = 4000

liveStreamStatus = fetchData.LiveStreamStatus(db_path, AUTO_CHECK)

def timeNowFunc():
    return liveStreamStatus.db.datetime_gmt(datetime.now())

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
@app_commands.describe(options="เลือกตัวเลือกที่ต้องการ", name="ชื่อ", istoday="วันนี้หรือไม่ True or False")
@app_commands.choices(
    options = [
        app_commands.Choice(name = "ชื่อช่อง", value = 0),
        app_commands.Choice(name = "รุ่น/บ้าน", value = 1),
        app_commands.Choice(name = "ค่าย", value = 2),
    ]
)
async def getLive(interaction, options: app_commands.Choice[int], name: str, istoday: bool=True):
    """Sends a greeting message to the specified user with an optional custom message."""
    await interaction.response.defer()
    listVtuber = []
    lis_embed = []
    try:
        txt = discordAuthChannel(interaction)
        if txt != None:
            await interaction.followup.send(txt)
            return
        
        # remove head and back white space
        name = name.strip()
        if options.value == 0:
            listVtuber = [db.getVtuber(name)]
        elif options.value == 1:
            listVtuber = db.listVtuberByGen(name)
        elif options.value == 2:
            listVtuber = db.listVtuberByGroup(name)
        else :
            embed = discordEmbed(
                title="ไม่พบข้อมูล",
                description=f"ไม่พบข้อมูล {name} ที่ต้องการ",
                color=discord.Color.yellow()
            )
            await interaction.followup.send(embeds=[embed])
            return
        
        if listVtuber == None or len(listVtuber) == 0 or listVtuber[0] == None:
            embed = discordEmbed(
                title="ไม่พบข้อมูล",
                description=f"ไม่พบข้อมูล {name} ที่ต้องการ",
                color=discord.Color.yellow()
            )
            await interaction.followup.send(embeds=[embed])
            return
        if "group_name" in listVtuber[0]:
            name = listVtuber[0]['group_name']
        elif "gen_name" in listVtuber[0]:
            name = listVtuber[0]['gen_name']
        else :
            name = listVtuber[0]['name']
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
                # strftime('%d %B %Y')
                start_at = datetime.strptime(
                    stream['start_at'].strftime("%Y-%m-%d"), "%Y-%m-%d"
                )
                timeNow = datetime.strptime(
                    timeNowFunc().strftime("%Y-%m-%d"), "%Y-%m-%d"
                )

                embedVtuber = discordEmbed(
                    title=v["name"],
                    description=f"ตารางไลฟ์ ประจำวันที่ {start_at.strftime('%d %B %Y')} ของ {v['name']}",
                    color=random_color()
                )
                embedVtuber.set_thumbnail(url=v["image"])
                
                # ตรวจสอบว่าในวันนี้มีไลฟ์หรือไม่

                # print(istoday, stream['title'], (istoday and start_at > timeNow), start_at < timeNow)
                if (istoday and start_at > timeNow) or (start_at < timeNow) :
                    continue
                found = True
                channel_link = f"https://www.youtube.com/@{stream['channel_tag']}/streams"
                embedVtuber.add_field(name='ชื่อไลฟ์', value=f"{stream['title']} [Link]({stream['url']})", inline=False)
                embedVtuber.add_field(name='เวลาไลฟ์', value=f"{stream['start_at'].strftime('%H:%M')} น.", inline=True)
                embedVtuber.add_field(name='สถานะ', value=f"{stream['live_status']}", inline=True)
                embedVtuber.add_field(name='ที่ช่อง', value=f"[{stream['channel_tag']}]({channel_link})", inline=True)
                embedVtuber.set_image(url=stream['image'])
                # embedVtuber.set_footer(text=f"Tag: {v['channel_tag']}")
                lis_embed.append(embedVtuber)
        if options.value == 0 and not found:
            embed = discordEmbed(
                title=listVtuber[0]["name"],
                description=f"ตอนนี้ {listVtuber[0]['channel_tag']} ยังไม่มีตารางไลฟ์",
                color=discord.Color.yellow()
            )
            await interaction.followup.send(embeds=[embed])
            return
        elif len(lis_embed) == 0:
            embed = discordEmbed(
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
        
        # await interaction.followup.send(embeds=lis_embed, ephemeral=True)

        # # Send the first embed
        message = await interaction.followup.send(embed=lis_embed[0], view=paginator)
        paginator.message = message  # Store the message for later access
    except Exception as e:
        print("Error: ", traceback.format_exc())
        await interaction.followup.send(f"Error: {e}")
        return

@client.tree.command(name='get-live-table', description="คำสั่งที่ดึงตารางไลฟ์ตามตัวเลือกที่คุณเลือก")
@app_commands.describe(group_name="ชื่อกลุ่ม", date="วันที่ต้องการ เช่น 1/12/2567")
async def getLiveTable(interaction: discord.Interaction, group_name: str, date: str=""):
    await interaction.response.defer()
    listVtuber = []
    listEmbed = []

    try:
        txt = discordAuthChannel(interaction)
        if txt != None:
            await interaction.followup.send(txt)
            return
        
        if date != "":
            date_obj = datetime.strptime(date, "%d/%m/%Y")
            date_obj = date_obj.replace(year=date_obj.year - 543)
        else:
            date_obj = timeNowFunc()

        group_name = group_name.strip()
        print(f"getLiveTable: {group_name}, {date_obj}")
        data_gen = db.listGenByGroup(group_name)
        if data_gen == None or len(data_gen) == 0:
            embed = discordEmbed(
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
            listVtuber = db.listVtuberByGen(gen_name)
            embedVtuber = discordEmbed(
                        title=f"ตารางไลฟ์ ประจำวันที่ {date_obj.strftime('%d %B %Y')} ของ {gen_name}",
                        color=random_color(),
                    )
            # embedVtuber.set_footer(text=f"Pages: {pageInfo}/{len(data_gen)}")
            embedVtuber.set_thumbnail(url=g['image'])
            if listVtuber == None or len(listVtuber) == 0 or listVtuber[0] == None:
                embedVtuber.add_field(name=f"ไม่มี Vtuber ใน Gen {gen_name} นี้", value="ไม่พบข้อมูล", inline=False)
                continue
            found = False
            for _, v in enumerate(listVtuber):
                # print(v["channel_tag"])
                if len(embedVtuber.fields) >= 25:
                    # print(f"Gen: {gen_name}")
                    listEmbed.append(embedVtuber)
                    pageInfo += 1
                    embedVtuber = discordEmbed(
                        title=f"ตารางไลฟ์ ประจำวันที่ {date_obj.strftime('%d %B %Y')} ของ {gen_name}",
                        color=random_color(),
                    )
                    # embedVtuber.set_footer(text=f"Pages: {pageInfo}/{len(data_gen)}")
                    embedVtuber.set_thumbnail(url=g['image'])
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
                        date_obj.strftime("%Y-%m-%d"), "%Y-%m-%d"
                    )
                    if (start_at != timeNow) :
                        continue

                    channel_link = f"https://www.youtube.com/@{stream['channel_tag']}/streams"
                    txt = f"{stream['title']} [Link]({stream['url']})"
                    embedVtuber.add_field(name=v["name"], value=txt, inline=False)
                    embedVtuber.add_field(name='เวลาไลฟ์', value=f"{stream['start_at'].strftime('%H:%M')} น.", inline=True)
                    embedVtuber.add_field(name='สถานะ', value=f"{stream['live_status']}", inline=True)
                    embedVtuber.add_field(name='ที่ช่อง', value=f"[{stream['channel_tag']}]({channel_link})", inline=True)
                    found = True
                    embedVtuber.add_field(name="----------------",value="" , inline=False)

            if not found:
                embedVtuber.add_field(name=f"ไม่พบไลฟ์ของ {gen_name} บน Youtube", value="ไม่พบไลฟ์บน Youtube", inline=False)

            # print(f"len embedVtuber: {len(embedVtuber.fields)}")
            listEmbed.append(embedVtuber)

        for i, v in enumerate(listEmbed):
            listEmbed[i].set_footer(text=f"Pages: {i+1}/{len(listEmbed)}")

        listEmbed = truncate_embed(listEmbed)
        # await interaction.followup.send(embeds=listEmbed)

        # TODO: ยังไม่ได้ใช้งาน 
        # interaction.followup.send("แสดงตารางไลฟ์...", ephemeral=True)
        # channel = client.get_channel(interaction.channel_id)
        # if len(listEmbed) >= 10:
        #     # split listEmbed into chunks of 10
        #     chunks = []
        #     index = -1
        #     for embed in listEmbed:
        #         if len(chunks) % 10 == 0:
        #             index += 1
        #             chunks.append([])
        #         chunks[index].append(embed)

        #     for chunk in chunks:
        #         await channel.send(embeds=chunk)
        # else:
        #     await channel.send(embeds=listEmbed)
        # await channel.send(embed=listEmbed)
        
        # Create the paginator view
        paginator = Paginator(embeds=listEmbed, timeout=60)

        # Send the first embed
        message = await interaction.followup.send(embed=listEmbed[0], view=paginator, ephemeral=True)
        paginator.message = message  # Store the message for later access

    except Exception as e:
        print(traceback.format_exc())
        await interaction.followup.send(f"เกิดข้อผิดพลาด: {e}", ephemeral=True)
        return


def truncate_embed(listEmbed: list) -> list:
    newListEmbed = []
    for embed in listEmbed:
        total_length = (
            len(embed.title or "")
            + len(embed.description or "")
            + sum(len(field.name) + len(field.value) for field in embed.fields)
            + len(embed.footer.text or "") if embed.footer else 0
        )
        
        if total_length <= MAX_EMBED_SIZE:
            newListEmbed.append(embed)
            continue

        # Truncate the description first
        if embed.description and len(embed.description) > 0:
            embed.description = embed.description[:MAX_EMBED_SIZE - total_length]
            total_length = len(embed.description)
        
        # Truncate fields if still exceeding limit
        for field in embed.fields:
            if total_length <= MAX_EMBED_SIZE:
                break
            field_length = len(field.name) + len(field.value)
            if field_length > 0:
                excess_length = total_length - MAX_EMBED_SIZE
                truncate_amount = min(len(field.value), excess_length)
                field.value = field.value[:-truncate_amount]
                total_length -= truncate_amount

        # Optionally truncate the footer if still exceeding
        if embed.footer and embed.footer.text and total_length > MAX_EMBED_SIZE:
            embed.footer.text = embed.footer.text[:MAX_EMBED_SIZE - total_length]
        
        newListEmbed.append(embed)
    return newListEmbed

@client.tree.command(name='update-live', description="คำสั่งที่อัพเดทข้อมูลตารางเผื่อว่ามีไลฟ์ที่มีการเปลี่ยนแปลง")
@app_commands.describe(
    options = "เลือกตัวเลือกที่ต้องการ",
    name = "ชื่อช่องที่ต้องการ"
)
@app_commands.choices(
    options = [
        app_commands.Choice(name = "ชื่อช่อง", value = 0),
        app_commands.Choice(name = "รุ่น/บ้าน", value = 1),
        app_commands.Choice(name = "ค่าย", value = 2),
    ]
)
async def updateLive(interaction: discord.Interaction, options: app_commands.Choice[int], name: str):
    await interaction.response.defer()
   
    listVtuber = []
    try:
        txt = discordAuthChannel(interaction)
        if txt != None:
            await interaction.followup.send(txt)
            return
        
        name = name.strip()
        if options.value == 0:
            listVtuber = [db.getVtuber(name)]
            if listVtuber[0]['name'] != None:
                name = listVtuber[0]['name']
            else:
                raise "ไม่พบชื่อช่องที่ค้นหา"
        elif options.value == 1:
            listVtuber = db.listVtuberByGen(name)
            if listVtuber[0]['gen_name'] != None:
                name = listVtuber[0]['gen_name']
            else:
                raise "ไม่พบรุ่น/บ้านที่ค้นหา"
        elif options.value == 2:
            listVtuber = db.listVtuberByGroup(name)
            if listVtuber[0]['group_name'] != None:
                name = listVtuber[0]['group_name']
            else:
                raise "ไม่พบค่ายที่ค้นหา"
        
        # if len(listVtuber) > 1:
        #     date_format = "%Y-%m-%d %H:%M:%S%z"
            
        #     time_now = liveStreamStatus.db.datetime_gmt(datetime.now())

        #     current_time = datetime.strptime(
        #         time_now.strftime(date_format), date_format
        #     )

        #     with open(ISUPDATE_PATH, "r") as file: 
        #         update_time = datetime.strptime(
        #             file.read(), date_format
        #         )
        #     if (current_time <= update_time):
        #         await interaction.followup.send(f"วันนี้ได้อัพเดทตารางของ {name} ไปเป็นที่เรียบร้อยแล้ว...")
        #         return
        #     else:
        #         next_update = time_now.replace(hour=14, minute=0, second=0) + timedelta(days=1)
        #         with open(ISUPDATE_PATH, "w") as file:
        #             file.write(next_update.strftime(date_format))

        if listVtuber == None or len(listVtuber) == 0 or listVtuber[0] == None:
            await interaction.followup.send(f"ไม่พบข้อมูล {name} ในฐานข้อมูล!")
            return
        message = await interaction.followup.send(f"อัพเดทข้อมูลตาราง {name} กําลังทําการอัพเดท...")
        for i, v in enumerate(listVtuber):
            liveStreamStatus.set_channel_id(v['channel_id'])
            # print(v['name'])
            await message.edit(content=f"อัพเดทข้อมูลตาราง {name} กําลังทําการอัพเดท... {i+1}/{len(listVtuber)}")
            _, err = await liveStreamStatus.live_stream_status(v['channel_id'])

        # await interaction.followup.send(f"อัพเดทข้อมูลตาราง {name} สําเร็จ...")
        # edit the message
        await message.edit(content=f"อัพเดทข้อมูลตาราง {name} สําเร็จ...")
    except Exception as e:
        print(traceback.format_exc())
        await interaction.followup.send(f"เกิดข้อผิดพลาด: {e}")

@client.tree.command(name='check-live-status', description="ตรวจสอบสถานะไลฟ์ของ Vtuber ที่คุณเลือก")
@app_commands.describe(
    options = "เลือกตัวเลือกที่ต้องการ",
    name = "ชื่อช่องที่ต้องการ"
)
@app_commands.choices(
    options = [
        app_commands.Choice(name = "ชื่อช่อง", value = 0),
        # app_commands.Choice(name = "รุ่น/บ้าน", value = 1),
        # app_commands.Choice(name = "ค่าย", value = 2),
    ]
)
async def checkLiveStatus(interaction: discord.Interaction, options: app_commands.Choice[int], name: str):
    await interaction.response.defer()
   
    listVtuber = []
    try:
        txt = discordAuthChannel(interaction)
        if txt != None:
            await interaction.followup.send(txt)
            return
        
        name = name.strip()
        if options.value == 0:
            listVtuber = [db.getVtuber(name)]
            name = listVtuber[0]['name']
        elif options.value == 1:
            listVtuber = db.listVtuberByGen(name)
            name = listVtuber[0]['gen_name']
        else:
            listVtuber = db.listVtuberByGroup(name)
            name = listVtuber[0]['group_name']
        if listVtuber == None or len(listVtuber) == 0 or listVtuber[0] == None:
            await interaction.followup.send(f"ไม่พบข้อมูล {name} ในฐานข้อมูล!")
            return

        for _, v in enumerate(listVtuber):
            msg = await liveStreamStatus.check_channel_status(v['channel_tag'])

        await interaction.followup.send(msg)
    except Exception as e:
        print(traceback.format_exc())
        await interaction.followup.send(f"เกิดข้อผิดพลาด: {e}")

class Paginator(discordView):
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

    @discordButton(label="First", style=discord.ButtonStyle.green)
    async def first_button(self, interaction: discord.Interaction, button: discordButton):
        if self.current_page > 0:
            self.current_page = 0
            self.update_button_states()  # Update button states
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    # Define the button for the previous page
    @discordButton(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discordButton):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_button_states()  # Update button states
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    # Define the button for the next page
    @discordButton(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discordButton):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self.update_button_states()  # Update button states
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discordButton(label="Last", style=discord.ButtonStyle.primary)
    async def last_button(self, interaction: discord.Interaction, button: discordButton):
        if self.current_page < len(self.embeds) - 1:
            self.current_page = len(self.embeds) - 1
            self.update_button_states()  # Update button states
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    async def on_timeout(self):
        # print("Timeout occurred: disabling buttons.")  # Log the timeout
        for item in self.children:
            item.disabled = True  # Disable all buttons
        await self.message.edit(view=self)  # Edit the message to update the view
        # await self.message.delete() # remove message after timeout

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        print(traceback.format_exc())

@client.tree.command(name='insert-new-channel', description="สร้างช่องใหม่ ถ้าเป็นอิสระก็ให้ว่างช่องรุ่น คำเตือนอย่าใช่บ่อยเกินไป !!!")
@app_commands.describe(username="ชื่อช่องเต็มเท่านั้น", gen_name="ชื่อรุ่น/บ้านเต็มเท่านั้น", group_name="ชื่อค่ายเต็มเท่านั้น")
async def insertNewChannel(interaction: discord.Interaction, username: str, gen_name: str=None, group_name: str=None):
    await interaction.response.defer()
    try:
        txt = discordAuthChannel(interaction)
        if txt != None:
            await interaction.followup.send(txt)
            return
        
        result = liveStreamStatus.insert_channel(username, gen_name, group_name)
        if result == None:
            raise ValueError("ไม่พบช่องที่ต้องการ")
        embed = discordEmbed(title="New Channel", color=random_color())
        embed.add_field(name="ชื่อช่อง", value=result['name'], inline=False)
        embed.add_field(name="Tag", value=f"@{result['youtube_tag']}", inline=False)
        embed.add_field(name="ชื่อรุ่น/บ้าน", value=result['gen_name'], inline=False)
        embed.add_field(name="ชื่อค่าย", value=result['group_name'], inline=False)
        embed.set_thumbnail(url=result['image'])
        await interaction.followup.send(embed=embed)
    except Exception as e:
        print(traceback.format_exc())
        await interaction.followup.send(f"เกิดข้อผิดพลาด: {e}")
        return

@client.tree.command(name='insert-video', description="สำหรับสร้างวีดีโอ/LiveStream ใหม่ ด้วยมือ")
async def insertVideo(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    try:
        txt = discordAuthChannel(interaction)
        if txt != None:
            await interaction.followup.send(txt)
            return

        video_id = url.replace("https://www.youtube.com/watch?v=", "")
        video_detail = await liveStreamStatus.get_live_stream_info(video_id)
        if video_detail == None:
            raise ValueError("ไม่พบวีดีโอที่ต้องการ")
        liveStreamStatus.db.checkLiveTable(video_detail)
        
    except Exception as e:
        await interaction.followup.send(f"เกิดข้อผิดพลาด: {e}")
        return

@client.tree.command(name='set-bot', description="ลงทะเบียนบอทลง Channel นี้")
@app_commands.choices(
    options2 = [
        app_commands.Choice(name = "ชื่อช่อง", value = 0),
        app_commands.Choice(name = "รุ่น/บ้าน", value = 1),
        app_commands.Choice(name = "ค่าย", value = 2),
    ]
)
@app_commands.describe(options1="เปิดให้ใช้งานคำสั่งที่ช่องนี้ใช่หรือไม่", options2="ต้องการแจ้งเตือนแบบไหน", name="ชื่อ", options3="เปิดแจ้งเตือนตอนเริ่มไลฟ์ที่ช่องนี้ใช่หรือไม่", options4="เปิดแจ้งเตือนก่อนเริ่มไลฟ์ที่ช่องนี้ใช่หรือไม่")
async def setBot(interaction: discord.Interaction, options1: bool, options2: app_commands.Choice[int], name: str, options3: bool=False, options4: bool=False):
    await interaction.response.defer()
    keyOption = {
        True: "เปิด",
        False: "ปิด"
    }
    try:
        channel = str(interaction.channel.id)
        guild = str(interaction.guild.id)
        name = name.strip()
        
        discord_id = db.checkDiscordServer(guild, channel, options1)
        embed = discordEmbed(
            title = "ลงทะเบียนบอทแจ้งเตือนไลฟ์",
            description = "ข้อมูลที่ลงทะเบียน",
            color=random_color(),
        )

        vtuber, gen, group = {'id': None}, {'id': None}, {'id': None}
        if options2.value == 0:
            vtuber = db.getVtuber(name)
            if vtuber == None:
                raise ValueError("ไม่พบชื่อช่อง")
            name = vtuber['name']
        elif options2.value == 1:
            gen = db.getGen(name)
            if gen == None:
                raise ValueError("ไม่พบชื่อรุ่น/บ้าน")
            name = gen['name']
        elif options2.value == 2:
            group = db.getGroup(name)
            if group == None:
                raise ValueError("ไม่พบชื่อค่าย")
            name = group['name']
        else:
            raise ValueError("ตัวเลือกไม่ถูกต้อง")
        
        data = {
            "discord_id": discord_id, 
            "default_vtuber_id": vtuber['id'], 
            "default_gen_id": gen['id'], 
            "default_group_id": group['id'], 
            "is_NotifyOnLiveStart": options3, 
            "Is_PreAlertEnabled": options4
        }
        db.checkDiscordMapping(data)

        embed.add_field(name="ใช้งานบอท", value=keyOption[options1], inline=True)
        embed.add_field(name=options2.name, value=name, inline=False)
        embed.add_field(name="ใช้งานแจ้งเตือน", value=keyOption[options3], inline=True)
        embed.add_field(name="ใช้งานแจ้งเตือนก่อนเริ่มไลฟ์", value=keyOption[options4], inline=False)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(traceback.format_exc())
        await interaction.followup.send(f"เกิดข้อผิดพลาด: {e}")
        return


@client.tree.command(name='test', description="สำหรับ Test เท่านั้น")
async def test(interaction: discord.Interaction, group_name: str):
    await interaction.response.defer()

    txt = discordAuthChannel(interaction)
    if txt != None:
        await interaction.followup.send(txt)
        return
    
    await interaction.followup.send(f"{group_name} สำหรับ Test เท่านั้น")
    return

def discordAuthChannel(interaction: discord.Interaction):
    channel = str(interaction.channel.id)
    guild = str(interaction.guild.id)

    if db.discordAuth(guild, channel):
        return None
    
    return "ไม่อนุญาตให้ใช้ Command ในช่องนี้"

def run_discord_bot(token: str):
    client.run(token)

# if __name__ == '__main__':
#     run_discord_bot()