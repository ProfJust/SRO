from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

db = client["robotik"]
collection = db["sensoren"]

daten = {
    "robot": "UR3e",
    "temperatur": 42.5
}

collection.insert_one(daten)

"""installieren Sie:

MongoDB Community Server
optional MongoDB Compass als grafische Oberfläche """