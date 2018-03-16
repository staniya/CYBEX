"""The Module interacting with the db."""
from cybeXtelegram.sourukorekuta import userbot, config
from telegram import Chat, Bot, ChatMember
from telegram.user import User
import psycopg2 as ps2
from psycopg2.extensions import connection as ps2conn
from psycopg2.extensions import cursor as ps2cursor

curdir = '/'.join(__file__.split('/')[:-1])


def runsql(sql: str, data: tuple = (), mogrify: bool = False) -> str:
    conn_string = 'dbname={0}'.format(config.db_name),\
                  'user={0}'.format(config.db_user),\
                  'password={0}'.format(config.db_password),\
                  'port={0}'.format(config.db_port)
    conn = ps2.connect(conn_string)  # type: ps2conn
    c = conn.cursor()  # type: ps2cursor
    if mogrify:
        return c.mogrify(sql, data)
    c.execute(sql, data)
    # result = c.mogrify(sql, data)
    try:
        result = c.fetchall()
    except ps2.ProgrammingError:
        result = None
    conn.commit()
    return result


def addgroup(chat: Chat) -> None:
    if chat.type != 'private':
        chatname = chat.title
    else:
        return
    chatid = str(chat.id).strip()

    if not runsql("SELECT id FROM shinnosuketaniya.groups WHERE id = {0};".format(chatid,)):
        channel = userbot.get_channel(chat.title)
        channel_id = channel.id  # type: int
        access_hash = channel.access_hash  # type: int
        runsql("INSERT INTO shinnosuketaniya.groups (id, "
               "name, "
               "channel_id, "
               "access_hash) "
               "VALUES ("
               "{0}, "
               "{1}, "
               "{2}, "
               "{3});".format(chatid, chatname, channel_id, access_hash))


def update_user(user: User, chat: Chat, msgtype: str, joindate: int = 0) -> None:
    if chat.type == 'private':
        return
    userid = str(user.id).strip()
    groupid = str(chat.id).strip()

    if not runsql("""SELECT shinnosuketaniya.statistics.user_id,
                            shinnosuketaniya.statistics.group_id 
                            FROM shinnosuketaniya.statistics 
                            WHERE shinnosuketaniya.statistics.user_id = {0} 
                            AND shinnosuketaniya.statistics.group_id = {1};
                            """.format(userid, groupid)):

        runsql("""INSERT INTO shinnosuketaniya.statistics (user_id,
                                             group_id,
                                             count_text,
                                             count_mention,
                                             count_hashtag,
                                             count_bot_command,
                                             count_url,
                                             count_email,
                                             count_photo,
                                             count_sticker,
                                             count_gif,
                                             count_video,
                                             count_voice,
                                             joindate,
                                             count_document) VALUES ( 
                                             {0},
                                             {1},
                                              0,
                                              0,
                                              0,
                                              0,
                                              0,
                                              0,
                                              0,
                                              0,
                                              0,
                                              0,
                                              0,
                                              {2},
                                              0);"""
               .format(userid, groupid, joindate))
    else:
        runsql("""UPDATE shinnosuketaniya.statistics 
                  SET count_{0} = count_{1} + 1 
                  WHERE user_id = {2}
                  AND group_id = {3};""".format(msgtype, msgtype, userid, groupid))


def add_user(user: User) -> None:
    userid = user.id
    fname = user.first_name
    lname = user.last_name
    uname = user.username
    if not runsql("SELECT id FROM shinnosuketaniya.users WHERE id = '{0}';".format(userid)):
        runsql("""INSERT INTO shinnosuketaniya.users (
                                                  id,
                                                  first_name,
                                                  last_name,
                                                  username
                                                  ) VALUES (
                                                  {0},
                                                  {1},
                                                  {2},
                                                  {3});""".format(
                                                  userid,
                                                  fname,
                                                  lname,
                                                  uname))


def get_active_user_ids(groupid: int) -> list:
    chatid = str(groupid).strip()
    active_members = runsql("""SELECT user_id 
                               FROM shinnosuketaniya.statistics 
                               WHERE group_id = {0};""".format(chatid,))
    active_members = [int(user[0]) for user in active_members]
    return active_members


def get_lurker_ids(groupid: int) -> list:
    chatid = str(groupid).strip()
    lurkers = runsql("""SELECT user_id
                              FROM shinnosuketaniya.statistics 
                              WHERE group_id = {0}
                              AND count_text = 0
                              OR count_mention = 0
                              OR count_hashtag = 0
                              OR count_bot_command = 0
                              OR count_url = 0
                              OR count_email = 0
                              OR count_photo = 0
                              OR count_sticker = 0
                              OR count_gif = 0
                              OR count_video = 0
                              OR count_voice = 0
                              OR count_document = 0;""".format(chatid, ))[0][0]
    lurkers = [user[0] for user in lurkers]
    return lurkers


def get_user(bot: Bot, userid: int, groupid: int) -> dict:
    chatid = str(groupid).strip()
    userrow = runsql("""SELECT * FROM shinnosuketaniya.statistics 
                        WHERE user_id = {0} AND group_id = {1}""".format(str(userid), chatid))[0]
    user = bot.get_chat_member(userrow[1], userrow[0])  # type: ChatMember
    userdict = {
        'first_name': str(user.user.first_name),
        'last_name': str(user.user.last_name),
        'username': str(user.user.username),
        'language_code': str(user.user.language_code),
        'status': str(user.status),
        'user_id': str(userrow[0]),
        'group_id': str(userrow[1]),
        'count_text': str(userrow[2]),
        'count_mention': str(userrow[3]),
        'count_hashtag': str(userrow[4]),
        'count_bot_command': str(userrow[5]),
        'count_url': str(userrow[6]),
        'count_email': str(userrow[7]),
        'count_photo': str(userrow[8]),
        'count_sticker': str(userrow[9]),
        'count_gif': str(userrow[10]),
        'count_video': str(userrow[11]),
        'count_voice': str(userrow[12]),
        'joined': str(userrow[13]),
        'count_document': str(userrow[14])
        }
    return userdict


def get_group(groupid: int) -> dict:
    chatid = str(groupid).strip()
    grouptuple = runsql("""SELECT * FROM shinnosuketaniya.groups 
                           WHERE id = {0}""".format(chatid, ))[0]
    active_members = runsql("""SELECT count(user_id) 
                              FROM shinnosuketaniya.statistics 
                              WHERE group_id = {0}
                              AND count_text > 0
                              OR count_mention > 0
                              OR count_hashtag > 0
                              OR count_bot_command > 0
                              OR count_url > 0
                              OR count_email > 0
                              OR count_photo > 0
                              OR count_sticker > 0
                              OR count_gif > 0
                              OR count_video > 0
                              OR count_voice > 0
                              OR count_document > 0;""".format(chatid, ))[0][0]

    lurkers = runsql("""SELECT count(user_id) 
                              FROM shinnosuketaniya.statistics 
                              WHERE group_id = {0}
                              AND count_text = 0
                              OR count_mention = 0
                              OR count_hashtag = 0
                              OR count_bot_command = 0
                              OR count_url = 0
                              OR count_email = 0
                              OR count_photo = 0
                              OR count_sticker = 0
                              OR count_gif = 0
                              OR count_video = 0
                              OR count_voice = 0
                              OR count_document = 0;""", (chatid, ))[0][0]
    group = {'chatid': grouptuple[0],
             'title': grouptuple[1],
             'channel_id': grouptuple[2],
             'access_hash': grouptuple[3],
             'active_members_count': active_members,
             'lurkers': lurkers}
    return group
