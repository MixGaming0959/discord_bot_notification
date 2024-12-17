import sqlite3
from datetime import datetime, timedelta, timezone
from os import environ, path
from uuid import uuid4
from rapidfuzz.fuzz import ratio as fuzz_ratio

from get_env import GetEnv

def gen_uuid():
    uuid_str = str(uuid4())
    varchar_uuid = uuid_str[:36]
    return varchar_uuid


class DatabaseManager:
    def __init__(self, db_name: str):
        env = GetEnv()
        self.ALREADY_LIVE = env.get_env_int("ALREADY_LIVE")
        self.BEFORE_LIVE = env.get_env_int("BEFORE_LIVE")
        self.GMT = env.get_env_int("GMT")
        self.CLEAR_LIVE_TABLE = env.get_env_str("CLEAR_LIVE_TABLE")
        # db_path = path.join(path.dirname(__file__), db_name)
        self.db_name = path.join(path.dirname(__file__), db_name)

    def datetime_gmt(self, datetime: datetime) -> datetime:
        tz = timezone(timedelta(hours=self.GMT))
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
            select id, name, youtubetag as channel_tag, image, channelid as channel_id, genid as gen_id, groupsid as group_id, isenable as is_enable
            from Vtuber
            where (UPPER(channelid) like UPPER('%{channel_id}%') or UPPER(youtubetag) like UPPER('%{channel_id}%') or UPPER(name) like UPPER('%{channel_id}%')) and isenable = 1
            ;
        """
        result = self.execute_query(query)
        if result and len(result) == 1:
            return dict(
                zip(
                    [
                        "id",
                        "name",
                        "channel_tag",
                        "image",
                        "channel_id",
                        "gen_id",
                        "group_id",
                        "is_enable",
                    ],
                    result[0],
                )
            )
        else:
            return None
        
    def getVtuber_for_insert(self, channel_id: str):
        query = f"""
            select id, name, youtubetag as channel_tag, image, channelid as channel_id, genid as gen_id, groupsid as group_id, isenable as is_enable
            from Vtuber
            where (UPPER(channelid) like UPPER('%{channel_id}%') or UPPER(youtubetag) like UPPER('%{channel_id}%') or UPPER(name) like UPPER('%{channel_id}%'))
            ;
        """
        result = self.execute_query(query)
        if result and len(result) == 1:
            return dict(
                zip(
                    [
                        "id",
                        "name",
                        "channel_tag",
                        "image",
                        "channel_id",
                        "gen_id",
                        "group_id",
                        "is_enable",
                    ],
                    result[0],
                )
            )
        else:
            return None

    def listVtuberByGroup(self, group_name: str):
        query = f"""
            select 
                v.id, v.name, v.youtubetag as channel_tag, v.image, channelid as channel_id, 
                CASE WHEN g.Another_Name is null then g.Name else g.Another_Name end as group_name
            from Vtuber v
            inner join groups g on v.groupsid = g.id
            where (UPPER(g.name) like UPPER('%{group_name}%') or UPPER(g.Another_Name) like UPPER('%{group_name}%')) and v.isenable = 1
        """
        result = self.execute_query(query)
        if result:
            return [
                dict(
                    zip(
                        [
                            "id",
                            "name",
                            "channel_tag",
                            "image",
                            "channel_id",
                            "group_name",
                        ],
                        row,
                    )
                )
                for row in result
            ]
        else:
            return None

    def listVtuberByGen(self, gen_name: str):
        query = f"""
            select v.id, v.name, v.youtubetag as channel_tag, v.image, channelid as channel_id, 
            CASE WHEN gen.Another_Name is null then gen.Name else gen.Another_Name end as gen_name
            from Vtuber v
            inner join generation gen on v.genid = gen.id
            where (UPPER(gen.name) like UPPER('%{gen_name}%') or UPPER(gen.Another_Name) like UPPER('%{gen_name}%')) and v.isenable = 1
        """
        result = self.execute_query(query)
        if result:
            return [
                dict(
                    zip(
                        [
                            "id",
                            "name",
                            "channel_tag",
                            "image",
                            "channel_id",
                            "gen_name",
                        ],
                        row,
                    )
                )
                for row in result
            ]
        else:
            return None

    def insertLiveTable(self, data: dict):
        query = """
            INSERT INTO LIVETABLE (Title, URL, StartAt, Colaborator, VtuberID, Image, LiveStatus)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = [
            (
                data["title"],
                data["url"],
                data["start_at"],
                data["colaborator"],
                data["vtuber_id"],
                data["image"],
                data["live_status"],
            )
        ]
        self.execute_many(
            query,
            params,
        )
        # print(query, params)

    def checkLiveTable(self, data: dict):
        query = """
            select 
                title, url, startat as start_at, colaborator, vtuber.youtubetag as channel_tag, livetable.image, vtuber.id as vtuber_id, livetable.livestatus as live_status, vtuber.channelid as channel_id, livetable.isnoti as is_noti
            from livetable
            inner join vtuber on livetable.vtuberid = vtuber.id
            where url = ?
            order by startat desc
            limit 1
        """

        result = self.execute_query(query, (data["url"],))
        result = [
            dict(
                zip(
                    [
                        "title",
                        "url",
                        "start_at",
                        "colaborator",
                        "channel_tag",
                        "image",
                        "vtuber_id",
                        "live_status",
                        "channel_id",
                        "is_noti",
                    ],
                    row,
                )
            )
            for row in result
        ]
        if len(result) == 0:
            self.insertLiveTable(data)
            # print("Insert Live Table Success")
            return data
        else:
            if (
                result[0]["title"] != data["title"]
                or result[0]["image"] != data["image"]
                or result[0]["start_at"] != data["colaborator"]
                or result[0]["live_status"] != data["live_status"]
            ):
                self.updateLiveTable(data)
                # print("Update Live Table Success")

        if type(result[0]["start_at"]) == str:
            dt = datetime.fromisoformat(result[0]["start_at"])
            data["start_at"] = dt.strftime("%Y-%m-%d %H:%M:%S")

        # Auto Delete
        self.clearLiveTable()
        return data

    def clearLiveTable(self):
        query = f"""
            delete from livetable
            where date(startat) <= DATE('now', '-{self.CLEAR_LIVE_TABLE} day')
        """
        self.execute_query(query)

    def updateLiveTable(self, data: dict):
        query = """
            update livetable
            set title = ?, url = ?, startat = ?, colaborator = ?, image = ?, livestatus = ?, isnoti = ?
            where url = ?
        """
        # is_noti in data ?

        isNoti = data["is_noti"] if "is_noti" in data else False
        self.execute_many(
            query,
            [
                (
                    data["title"],
                    data["url"],
                    data["start_at"],
                    data["colaborator"],
                    data["image"],
                    data["live_status"],
                    isNoti,
                    data["url"],
                )
            ],
        )

    def getLiveTablebyURL(self, url: list):
        conditon = ",".join(
            ["'https://www.youtube.com/watch?v={}'".format(x) for x in url]
        )
        query = f"""
            select title, url, startat as start_at, colaborator, vtuber.youtubetag as channel_tag, livetable.image, vtuber.id as vtuber_id, livetable.livestatus as live_status, vtuber.channelid as channel_id, livetable.isnoti as is_noti
            from livetable
            inner join vtuber on livetable.vtuberid = vtuber.id
            where url in ({conditon})
            order by start_at asc;
        """
        result = self.execute_query(query)
        if result:
            return [
                dict(
                    zip(
                        [
                            "title",
                            "url",
                            "start_at",
                            "colaborator",
                            "channel_tag",
                            "image",
                            "vtuber_id",
                            "live_status",
                            "channel_id",
                            "is_noti",
                        ],
                        row,
                    )
                )
                for row in result
            ]
        else:
            return []

    def getLiveTable(self, channelTag: str):
        query = f"""
            select title, url, startat as start_at, colaborator, vtuber.youtubetag as channel_tag, livetable.image, vtuber.id as vtuber_id, livetable.livestatus as live_status, vtuber.channelid as channel_id, livetable.isnoti as is_noti
            from livetable
            inner join vtuber on livetable.vtuberid = vtuber.id
            where (UPPER(colaborator) like UPPER('%{channelTag}%') or UPPER(vtuber.youtubetag) like UPPER('{channelTag}')) and livetable.livestatus != 'none'
            order by 
                CASE 
                        WHEN UPPER(vtuber.youtubetag) = UPPER('{channelTag}') THEN 0 -- ชื่อที่ต้องการให้ขึ้นก่อน
                        ELSE 1
                    END, 
                    vtuber.youtubetag, -- ลำดับต่อไปตามปกติ (เรียงตามตัวอักษร)
                start_at asc;
        """
        result = self.execute_query(query)
        if result:
            return [
                dict(
                    zip(
                        [
                            "title",
                            "url",
                            "start_at",
                            "colaborator",
                            "channel_tag",
                            "image",
                            "vtuber_id",
                            "live_status",
                            "channel_id",
                            "is_noti",
                        ],
                        row,
                    )
                )
                for row in result
            ]
        else:
            return None

    def getLiveTable_30(self):
        dt_past = self.datetime_gmt(
            datetime.now() - timedelta(minutes=self.BEFORE_LIVE)
        )
        dt_future = self.datetime_gmt(
            datetime.now() + timedelta(minutes=self.BEFORE_LIVE)
        )
        query = f"""
            select title, url, startat as start_at, colaborator, 
            vtuber.youtubetag as channel_tag, livetable.image, 
            vtuber.id as vtuber_id, livetable.livestatus as live_status,
            vtuber.channelid as channel_id, isnoti as is_noti, vtuber.name as channel_name
            from livetable
            inner join vtuber on livetable.vtuberid = vtuber.id
            where livetable.livestatus in ('upcoming', 'live') and start_at > '{dt_past}' and start_at < '{dt_future}'
            order by start_at asc;
        """
        result = self.execute_query(query)
        if result:
            return [
                dict(
                    zip(
                        [
                            "title",
                            "url",
                            "start_at",
                            "colaborator",
                            "channel_tag",
                            "image",
                            "vtuber_id",
                            "live_status",
                            "channel_id",
                            "is_noti",
                            "channel_name",
                        ],
                        row,
                    )
                )
                for row in result
            ]
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
        query = 'select CASE WHEN g.Another_Name is null then g.Name else g.Another_Name end as name from "groups" g'
        result = self.execute_query(query)
        if result:
            return [dict(zip(["name"], row)) for row in result]
        else:
            return []

    def listGen(self):
        query = "select CASE WHEN gen.Another_Name is null then gen.Name else gen.Another_Name end as name from generation gen"
        result = self.execute_query(query)
        if result:
            return [dict(zip(["name"], row)) for row in result]
        else:
            return []

    def listVtuber(self):
        query = 'select name from "vtuber"'
        result = self.execute_query(query)
        if result:
            return [dict(zip(["name"], row)) for row in result]
        else:
            return []

    def listGenByGroup(self, group_name: str):
        query = f"""
            select 
                gen.id, 
                CASE WHEN gen.Another_Name is null then gen.Name else gen.Another_Name end as name, 
                gen.groupsid as group_id, gen.image
            from groups g
            inner join generation gen on gen.groupsid = g.id
            where UPPER(g.name) like UPPER('%{group_name}%') or UPPER(g.Another_Name) like UPPER('%{group_name}%');
        """
        result = self.execute_query(query)
        if result:
            return [
                dict(zip(["id", "name", "group_id", "image"], row)) for row in result
            ]
        else:
            return None

    def insertDiscordServer(self, data: dict):
        uuid = gen_uuid()
        query = f"""
            insert into discordserver (id, guildid, channelid, is_active)
            values ('{uuid}', ?, ?, ?);
        """
        self.execute_many(
            query,
            [(data["guild_id"], data["channel_id"], data["is_active"])],
        )
        return uuid

    def updateDiscordServer(self, data: dict):
        query = f"""
            update discordserver
            set is_active = ?
            where guildid = ? and channelid = ?
        """
        self.execute_many(
            query,
            [(data["is_active"], data["guild_id"], data["channel_id"])],
        )

    def checkDiscordServer(
        self, guild_id: str, channel_id: str, is_active: bool
    ) -> str:
        query = f"""
            select id from discordserver
            where guildid = ? and channelid = ?
            limit 1;
        """
        result = self.execute_query(
            query,
            (
                guild_id,
                channel_id,
            ),
        )
        if result:
            self.updateDiscordServer(
                {"guild_id": guild_id, "channel_id": channel_id, "is_active": is_active}
            )
            result = [dict(zip(["id"], row)) for row in result]
            discord_id = str(result[0]["id"])
        else:
            discord_id = self.insertDiscordServer(
                {"guild_id": guild_id, "channel_id": channel_id, "is_active": is_active}
            )
        # return id str
        return discord_id

    def insertDiscordMapping(self, data: dict):
        uuid = gen_uuid()
        query = f"""
            insert into discord_mapping (id, discord_id, defaultvtuber_id, defaultgen_id, defaultgroup_id, is_NotifyOnLiveStart, Is_PreAlertEnabled)
            values (?, ?, ?, ?, ?, ?, ?);
        """
        self.execute_many(
            query,
            [
                (
                    uuid,
                    data["discord_id"],
                    data["default_vtuber_id"],
                    data["default_gen_id"],
                    data["default_group_id"],
                    data["is_NotifyOnLiveStart"],
                    data["Is_PreAlertEnabled"],
                )
            ],
        )
        return uuid

    def updateDiscordMapping(self, data: dict):
        query = f"""
            update discord_mapping
            set defaultvtuber_id = ?, defaultgen_id = ?, defaultgroup_id = ?, is_NotifyOnLiveStart = ?, Is_PreAlertEnabled = ?
            where discord_id = ?
        """
        self.execute_many(
            query,
            [
                (
                    data["default_vtuber_id"],
                    data["default_gen_id"],
                    data["default_group_id"],
                    data["is_NotifyOnLiveStart"],
                    data["Is_PreAlertEnabled"],
                    data["discord_id"],
                )
            ],
        )

    def checkDiscordMapping(self, data: dict) -> str:
        query = f"""
            select id from discord_mapping
            where discord_id = ?
            limit 1;
        """
        result = self.execute_query(query, (data["discord_id"],))
        if result:
            result = [dict(zip(["id"], row)) for row in result]
            self.updateDiscordMapping(data)
            discord_mapping_id = str(result[0]["id"])
        else:
            discord_mapping_id = self.insertDiscordMapping(data)
        return discord_mapping_id

    def updateImageVtuber(self, data: dict):
        vtuber = self.getVtuber(data["youtube_tag"])
        if vtuber == None:
            self.InsertVtuber(
                {
                    "name": data["name"],
                    "youtube_tag": data["youtube_tag"],
                    "gen_name": data["gen_name"],
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
            query,
            [(data["image"], data["youtube_tag"].title())],
        )

    def insertVtuber(self, data: dict):
        gen, group = {"id": None}, {"id": None}
        # check vtuber has already in database?
        vtuber = self.getVtuber_for_insert(data["youtube_tag"])
        if vtuber is not None:
            raise Exception(f"{vtuber['name']} has already in database")

        if data["group_name"] is not None:
            group = self.getGroup(data["group_name"])
            if group is None:
                self.insertGroup(data["group_name"])
                group = self.getGroup(data["group_name"])
        else:
            group = self.getGroup(data["name"])
            if group is None:
                self.insertGroup(data["name"])
                group = self.getGroup(data["name"])

        if data["gen_name"] is not None:
            gen = self.getGen(data["gen_name"], group["name"])
            if gen == None:
                self.insertGen(
                    {
                        "name": data["gen_name"],
                        "group_name": group["name"],
                        "image": data["image"],
                    }
                )
                gen = self.getGen(data["gen_name"], group["name"])

        query = f"""
            insert into vtuber (ID, Name, GenID, GroupsID, YoutubeTag, Image, ChannelID, IsEnable)
            values (?, ?, ?, ?, ?, ?, ?, ?);
        """
        self.execute_many(
            query,
            [
                (
                    gen_uuid(),
                    data["name"],
                    gen["id"],
                    group["id"],
                    data["youtube_tag"].title(),
                    data["image"],
                    data["channel_id"],
                    1,
                )
            ],
        )

    def getGen(self, genName: str, groupName: str, image: str = ""):

        query = f"""
            select g1.id, 
            CASE WHEN g1.Another_Name is null then g1.Name else g1.Another_Name end as name,
            g1.groupsid as groups_id
            from generation g1
            inner join groups g2 on g1.groupsid = g2.id
            WHERE (UPPER(g1.Name) like UPPER('%{genName}%') OR UPPER(g1.Another_Name) like UPPER('%{genName}%') AND (UPPER(g2.Name) like UPPER('%{groupName}%') OR UPPER(g2.Another_Name) like UPPER('%{groupName}%')))
        """
        result = self.execute_query(query)
        if result:
            return dict(zip(["id", "name", "groups_id"], result[0]))
        else:
            return None

    def insertGen(self, data: dict):
        group = self.getGroup(data["group_name"])

        query = f"""
            insert into generation (id,name, groupsid, image)
            values (?, ?, ?, ?);
        """
        self.execute_many(
            query,
            [(gen_uuid(), data["name"].title(), group["id"], data["image"])],
        )

    def getGroup(self, groupName: str):
        query = f"""
            select g.id, 
            CASE WHEN g.Another_Name is null then g.Name else g.Another_Name end as name
            from groups g
            where UPPER(g.name) like UPPER('%{groupName}%') or UPPER(g.Another_Name) like UPPER('%{groupName}%')
            limit 1;
        """
        # print(query)
        result = self.execute_query(query)
        if result:
            return dict(zip(["id", "name"], result[0]))
        else:
            return None

    def insertGroup(self, name: str):
        query = f"""
            insert into groups (id,name)
            values (?, ?);
        """
        self.execute_many(
            query,
            [(gen_uuid(), name.title())],
        )

    def simpleCheckSimilarity(self, target: list, source: str) -> str:
        result = []
        for v in target:
            result.append({v: fuzz_ratio(source, str(v)) / 100})

        # sort by similarity
        result = sorted(result, key=lambda x: list(x.values())[0], reverse=True)
        return list(result[0].keys())[0]

    def getDiscordDetails(
        self, vtuber_id: list = None, gen_id: list = None, group_id: list = None
    ) -> list:
        """
        Get discord server details by vtuber_id, gen_id, or group_id
        """
        query = """
            select 
                ds.id, ds.guildid as guild_id, ds.channelid as channel_id, dm.is_NotifyOnLiveStart, dm.is_PreAlertEnabled
            from discordserver ds
            inner join discord_mapping dm on ds.id = dm.discord_id and ds.is_active = 1 and (dm.is_NotifyOnLiveStart = 1 or dm.is_PreAlertEnabled = 1)
        """
        conditions = []
        if vtuber_id:
            vtuber_id = ",".join(["'{}'".format(x) for x in vtuber_id])
            conditions.append(f" dm.DefaultVtuber_ID in ({vtuber_id})")
        if gen_id:
            gen_id = ",".join(["'{}'".format(x) for x in gen_id])
            conditions.append(f" dm.DefaultGen_ID in ({gen_id})")
        if group_id:
            group_id = ",".join(["'{}'".format(x) for x in group_id])
            conditions.append(f" dm.DefaultGroup_ID in ({group_id})")
        if conditions:
            query += " where " + " or ".join(conditions)
        result = self.execute_query(query)
        if result:
            return [
                dict(
                    zip(
                        [
                            "id",
                            "guild_id",
                            "channel_id",
                            "is_NotifyOnLiveStart",
                            "is_PreAlertEnabled",
                        ],
                        row,
                    )
                )
                for row in result
            ]
        else:
            return []

    def discordAuth(self, discord_id: str, channel_id: str):
        query = f"""
            select * from discordserver ds where ds.guildid = '{discord_id}' and ds.channelid = '{channel_id}' and ds.is_active = 1;
        """
        result = self.execute_query(query)
        if result:
            return True
        else:
            return False


if __name__ == "__main__":
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
    from os import environ

    db = DatabaseManager(environ.get("DB_PATH"))

    print(db.getLiveTable_30())

    # print("123 " + " and ".join(["1", "2"]))
    # print(db.getLiveTable('SisiraHydrangea'))
