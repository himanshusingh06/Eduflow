from pymongo import MongoClient

client = MongoClient("mongodb+srv://himanshuks062_db_user:O6Sum87JAnhmTNfW@cluster0.ac6fb5c.mongodb.net/")
print(client.list_database_names())
