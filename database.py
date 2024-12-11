import sqlite3
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv # type: ignore
load_dotenv()
from os import environ, path

from uuid import uuid4

def load_env_json(key:str):
    return environ.get(key)
def gen_uuid():
        uuid_str = str(uuid4())
        varchar_uuid = uuid_str[:36]
        return varchar_uuid

class DatabaseManager:
    def __init__(self, db_name:str):
        # db_path = path.join(path.dirname(__file__), db_name)
        self.db_name = path.join(path.dirname(__file__), db_name)

    def datetime_gmt(self, datetime:datetime) -> datetime:
        gmt = int(load_env_json('GMT'))
        tz = timezone(timedelta(hours=gmt))
        new_time = datetime.astimezone(tz)
        return new_time

    def connect(self):
        return sqlite3.connect(self.db_name)

    def execute_query(self, query, params=None):
        with self.connect() as conn:
            try:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.fetchall()
            except Exception as e:
                conn.rollback()
                raise e


    def execute_many(self, query, data):
        with self.connect() as conn:
            try:
                cursor = conn.cursor()
                cursor.executemany(query, data)
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e

    def getVtuber(self, channel_id: str):
        query = f"""
            select id, name, youtubetag as channel_tag, image, channelid as channel_id, genid as gen_id, groupsid as group_id
            from Vtuber
            where (channelid like '%{channel_id}%' or youtubetag like '%{channel_id}%' or name like '%{channel_id}%') and isenable = 1
            ;
        """
        result = self.execute_query(query)
        if result and len(result) == 1:
            return dict(zip(['id', 'name', 'channel_tag', 'image', 'channel_id', 'gen_id', 'group_id'], result[0]))
        else:
            return None
    
    def listVtuberByGroup(self, group_name: str):
        query = f"""
            select v.id, v.name, v.youtubetag as channel_tag, v.image, channelid as channel_id, g.name as group_name
            from Vtuber v
            inner join groups g on v.groupsid = g.id
            where g.name like '%{group_name}%' and v.isenable = 1
        """
        result = self.execute_query(query)
        if result:
            return [dict(zip(['id', 'name', 'channel_tag', 'image', 'channel_id', 'group_name'], row)) for row in result]
        else:
            return None
    
    def listVtuberByGen(self, gen_name: str):
        query = f"""
            select v.id, v.name, v.youtubetag as channel_tag, v.image, channelid as channel_id, gen.name as gen_name
            from Vtuber v
            inner join generation gen on v.genid = gen.id
            where gen.name like '%{gen_name}%' and v.isenable = 1
        """
        result = self.execute_query(query)
        if result:
            return [dict(zip(['id', 'name', 'channel_tag', 'image', 'channel_id', 'gen_name'], row)) for row in result]
        else:
            return None
        
    def insertLiveTable(self, data: dict):
        query = """
            INSERT INTO LIVETABLE (Title, URL, StartAt, Colaborator, VtuberID, Image, LiveStatus)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = [(data["title"], data["url"], data["start_at"], data["colaborator"], data["vtuber_id"], data["image"], data["live_status"])]
        self.execute_many(
            query, params,
        )
        # print(query, params)
    
    def checkLiveTable(self, data: dict):
        query = """
            select 
                title, url, startat as start_at, colaborator, vtuber.youtubetag as channel_tag, livetable.image, vtuber.id as vtuber_id, livetable.livestatus as live_status, vtuber.channelid as channel_id
            from livetable
            inner join vtuber on livetable.vtuberid = vtuber.id
            where url = ?
            order by startat desc
            limit 1
        """

        result = self.execute_query(query, (data["url"],))
        result = [dict(zip(['title', 'url', 'start_at', 'colaborator', 'channel_tag', 'image', 'vtuber_id', 'live_status', 'channel_id'], row)) for row in result]
        if len(result) == 0:
            self.insertLiveTable(data)
            # print("Insert Live Table Success")
            return data
        else:
            if result[0]['title'] != data['title'] or result[0]['image'] != data['image'] or result[0]['start_at'] != data['colaborator'] or result[0]['live_status'] != data['live_status']:
                self.updateLiveTable(data)
                # print("Update Live Table Success")
                
        if type(result[0]['start_at']) == str:
            dt = datetime.fromisoformat(result[0]['start_at'])
            data['start_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
            
        # Auto Delete
        self.deleteLiveTable()
        return data
    
    def deleteLiveTable(self):
        query = """
            delete from livetable
            where date(startat) <= DATE('now', '-2 day')
        """
        self.execute_query(query)

    def updateLiveTable(self, data: dict):
        query = """
            update livetable
            set title = ?, url = ?, startat = ?, colaborator = ?, image = ?, livestatus = ?
            where url = ?
        """
        self.execute_many(
            query,[(data["title"], data["url"], data["start_at"], data["colaborator"], data["image"], data['live_status'], data["url"])],
        )
    
    def getLiveTable(self, channelTag: dict):
        query = f"""
            select title, url, startat as start_at, colaborator, vtuber.youtubetag as channel_tag, livetable.image, vtuber.id as vtuber_id, livetable.livestatus as live_status, vtuber.channelid as channel_id
            from livetable
            inner join vtuber on livetable.vtuberid = vtuber.id
            where (colaborator like '%{channelTag}%' or vtuber.youtubetag like '{channelTag}') and livetable.livestatus != 'none'
            order by 
                CASE 
                        WHEN vtuber.youtubetag = '{channelTag}' THEN 0 -- ชื่อที่ต้องการให้ขึ้นก่อน
                        ELSE 1
                    END, 
                    vtuber.youtubetag, -- ลำดับต่อไปตามปกติ (เรียงตามตัวอักษร)
                start_at asc;
        """
        result = self.execute_query(query)
        if result:
            return [dict(zip(['title', 'url', 'start_at', 'colaborator', 'channel_tag', 'image', 'vtuber_id', 'live_status', 'channel_id'], row)) for row in result]
        else:
            return None
    # ยก Live
    def cancelLiveTable(self, url: str, livestatus: str):
        query = f"""
            update livetable
            set livestatus = ?
            where url = ?
        """
        self.execute_many(query, [(livestatus, url)])
        
    def listGroup(self):
        query = 'select name from \"groups\"'
        result = self.execute_query(query)
        if result:
            return [dict(zip(['name'], row)) for row in result]
        else:
            return None
    
    def listGenByGroup(self, group_name: str):
        query = f"""
            select gen.id, gen.name, gen.groupsid as group_id, gen.image
            from groups g
            inner join generation gen on gen.groupsid = g.id
            where g.name like '%{group_name}%'
        """
        result = self.execute_query(query)
        if result:
            return [dict(zip(['id', 'name', 'group_id', 'image'], row)) for row in result]
        else:
            return None
        
    def listDiscordServer(self):
        query = 'select id, guildid as guild_id, channelid as channel_id, defaultvtuber as default_vtuber, defaultgen, as defaultgen, defaultgroup as default_group from discordserver'
        result = self.execute_query(query)
        return [dict(zip(['ID','guild_id', 'channel_id', 'default_vtuber', 'default_gen', 'default_group'], row)) for row in result]
    
    def updateImageVtuber(self, data: dict):
        vtuber = self.getVtuber(data["youtube_tag"])
        if vtuber == None:
            self.InsertVtuber(
                {
                    "name": data["name"],
                    "youtube_tag": data["youtube_tag"],
                    "gen_name": data['gen_name'],
                    "group_name": data["group_name"],
                    "image": data["image"],
                    "channel_id": data["channel_id"],
                }
            )
            return
        
        query = f"""
            UPDATE VTUBER
            SET Image = ?
            WHERE YoutubeTag = ?
        """
        self.execute_many(
            query,[(data["image"], data["youtube_tag"])],
        )

    def insertVtuber(self, data: dict):
        group = self.getGroup(data["group_name"])
        if group == None:
            self.insertGroup(data["group_name"])
            group = self.getGroup(data["group_name"])
        gen = self.getGen(data["gen_name"], group["name"])
        if gen == None:
            self.insertGen({"name": data["gen_name"], "group_name": group["name"], "image": data["image"]})
            gen = self.getGen(data["gen_name"], group["name"])
        query = f"""
            insert into vtuber (ID, Name, GenID, GroupsID, YoutubeTag, Image, ChannelID, IsEnable)
            values (?, ?, ?, ?, ?, ?, ?)
        """
        self.execute_many(
            query,[(data["name"], gen["id"], group["id"], data["youtube_tag"], data["image"], data["channel_id"], 1)],
        )
    
    def getGen(self, genName: str, groupName: str, image: str = ""):
        
        query = f"""
            select g1.id, g1.name, g1.groupsid as groups_id
            from generation g1
            inner join groups g2 on g1.groupsid = g2.id
            WHERE g1.Name like '%{genName}%' AND g2.Name like '%{groupName}%'
        """
        result = self.execute_query(query)
        if result:
            return dict(zip(['id', 'name', 'groups_id'], result[0]))
        else:
            return None
    
    def insertGen(self, data: dict):
        group = self.getGroup(data["group_name"])
        id = gen_uuid().hex
        query = f"""
            insert into generation (id,name, groupsid, image)
            values (?, ?, ?, ?);
        """
        self.execute_many(
            query,[( gen_uuid(),data["name"], group["id"], data["image"])],
        )
        
    def getGroup(self, groupName: str):
        query = f"""
            select id, name
            from groups
            where name like '%{groupName}%';
        """
        # print(query)
        result = self.execute_query(query)
        if result:
            return dict(zip(['id', 'name'], result[0]))
        else:
            return None

    
    def insertGroup(self, name: str):
        query = f"""
            insert into groups (id,name)
            values ({gen_uuid()},'{name});
        """
        self.execute_query(query)
    
    def simpleCheckSimilarity(self, target: str, source: str) -> bool:
        query = f"""
            select * from (
            select '{source}' as name
            ) as c2
            where c2.name like '%{target}%'
        """

        result = self.execute_query(query)
        if result:
            return True
        else:
            return False
        
    def getDiscordDetails(self, vtuber_id: str = None, gen_id: str = None, group_id: str = None) -> list:
        """
        Get discord server details by vtuber_id, gen_id, or group_id
        """
        query = """
            select 
                ds.id, ds.guildid as guild_id, ds.channelid as channel_id
            from discordserver ds
            inner join discord_mapping dm on ds.id = dm.discord_id
        """
        conditions = []
        if vtuber_id:
            conditions.append(f" dm.DefaultVtuber_ID = '{vtuber_id}'")
        if gen_id:
            conditions.append(f" dm.DefaultGen_ID = '{gen_id}'")
        if group_id:
            conditions.append(f" dm.DefaultGroup_ID = '{group_id}'")
        if conditions:
            query += " where " + " or ".join(conditions)
        result = self.execute_query(query)
        if result:
            return [dict(zip(['id', 'guild_id', 'channel_id'], row)) for row in result]
        else:
            return []

if __name__ == '__main__':
    from dotenv import load_dotenv # type: ignore
    load_dotenv()
    from os import environ
    
    # print("123 " + " and ".join(["1", "2"]))
    # print(db.getLiveTable('SisiraHydrangea'))