from pymongo import MongoClient
# from sshtunnel import SSHTunnelForwarder

MONGO_HOST = "47.52.20.196"
MONGO_DB = "cybex_user_management"
MONGO_USER = "staniya"
MONGO_PASS = "password"


# server = SSHTunnelForwarder(
#     MONGO_HOST,
#     ssh_username=MONGO_USER,
#     ssh_passsword=MONGO_PASS,
#     remote_bind_address=('127.0.0.1', 27017)
# )


def connect_db():
    # server.start()
    # client = MongoClient('127.0.0.1', server.local_bind_port)
    db = MongoClient()['cybex_user_management']
    db.user.create_index('username', unique=True)
    db.joined_user.create_index([('chat_id', 1), ('user_id', 1)])
    db.event.create_index([('type', 1), ('date', 1)])
    db.day_stat.create_index('date')
    return db
