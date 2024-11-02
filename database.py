import sqlite3
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv # type: ignore
load_dotenv()
from os import environ, path

def load_env_json(key:str):
    return environ.get(key)

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
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()

    def execute_many(self, query, data):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, data)
            conn.commit()

    def getVtuber(self, channel_id: str):
        query = f"""
            select id, name, youtubetag as channel_tag, image, channelid as channel_id
            from Vtuber
            where (channelid like '%{channel_id}%' or youtubetag like '%{channel_id}%' or name like '%{channel_id}%') and isenable = 1
            LIMIT 1;
        """
        result = self.execute_query(query)
        if result:
            return dict(zip(['id', 'name', 'channel_tag', 'image', 'channel_id'], result[0]))
        else:
            return None
    
    def listVtuberByGroup(self, group_name: str):
        query = f"""
            select v.id, v.name, v.youtubetag as channel_tag, v.image, channelid as channel_id
            from Vtuber v
            inner join "group" g on v.groupid = g.id
            where g.name like '%{group_name}%' and v.isenable = 1
        """
        result = self.execute_query(query)
        if result:
            return [dict(zip(['id', 'name', 'channel_tag', 'image', 'channel_id'], row)) for row in result]
        else:
            return None
    
    def listVtuberByGen(self, gen_name: str):
        query = f"""
            select v.id, v.name, v.youtubetag as channel_tag, v.image, channelid as channel_id
            from Vtuber v
            inner join "gen" gen on v.genid = gen.id
            where gen.name like '%{gen_name}%' and v.isenable = 1
        """
        result = self.execute_query(query)
        if result:
            return [dict(zip(['id', 'name', 'channel_tag', 'image', 'channel_id'], row)) for row in result]
        else:
            return None
        
    def insertLiveTable(self, data: dict):
        query = """
            INSERT INTO LIVETABLE (Title, URL, StartAt, Colaborator, VtuberID, Image, LiveStatus)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.execute_many(
            query,
            [(data["title"], data["url"], data["start_at"], data["colaborator"], int(data['vtuber_id']), data["image"], data["live_status"])],
        )
    
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
            if result[0]['title'] != data['title'] or result[0]['image'] != data['image']:
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
            order by start_at asc;
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
        print([(livestatus, url)])
        self.execute_many(query, [(livestatus, url)])
        
    def listGroup(self):
        query = 'select name from \"group\"'
        result = self.execute_query(query)
        if result:
            return [dict(zip(['name'], row)) for row in result]
        else:
            return None
    
    def listGenByGroup(self, group_name: str):
        query = f"""
            select gen.id, gen.name, gen.groupid as group_id, gen.image
            from "group" g
            inner join "gen" gen on gen.groupid = g.id
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
        gen = self.getGen(data["gen_name"], group["name"])
        query = f"""
            insert into vtuber (Name, GenID, GroupID, YoutubeTag, Image, ChannelID, IsEnable)
            values (?, ?, ?, ?, ?, ?, ?)
        """
        self.execute_many(
            query,[(data["name"], gen["id"], group["id"], data["youtube_tag"], data["image"], data["channel_id"], 1)],
        )
    
    def getGen(self, genName: str, groupName: str, image: str = ""):
        
        query = f"""
            select g1.id, g1.name, g1.groupid
            from "gen" g1
            inner join "group" g2 on g1.groupid = g2.id
            WHERE g1.Name like '%{genName}%' AND g2.Name like '%{groupName}%'
        """
        result = self.execute_query(query)
        if result:
            return dict(zip(['id', 'name', 'groupid'], result[0]))
        else:
            # return None
            # insert new gen
            self.insertGen({"name": genName, "group_name": groupName, "image": image})
            return self.getGen(genName, groupName)
    
    def insertGen(self, data: dict):
        group = self.getGroup(data["group_name"])
        query = f"""
            insert into "gen" (name, groupid, image)
            values (?, ?, ?);
        """
        self.execute_many(
            query,[(data["name"], group["id"], data["image"])],
        )
        
    def getGroup(self, groupName: str):
        query = f"""
            select id, name
            from "group"
            where name like '%{groupName}%';
        """
        # print(query)
        result = self.execute_query(query)
        if result:
            return dict(zip(['id', 'name'], result[0]))
        else:
            # return None
            # insert new group
            self.insertGroup(groupName)
            return self.getGroup(groupName)
    
    def insertGroup(self, name: str):
        query = f"""
            insert into "group" (name)
            values (?)
        """
        self.execute_many(
            query,[(name)],
        )
    
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

if __name__ == '__main__':
    from dotenv import load_dotenv # type: ignore
    load_dotenv()
    from os import environ
    
    db = DatabaseManager(environ.get('DB_PATH'))
    
    print(db.getVtuber('KeressaZoulfia'))