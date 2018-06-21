from pymongo import MongoClient


def connect_db():
    db = MongoClient()['ico_ape_member_count']
    db.links.create_index('link_name', unique=True)
    db.user_numbers.create_index('link', 1)
    return db