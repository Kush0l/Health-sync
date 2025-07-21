from pymongo import MongoClient

class Database:
    def __init__(self):
        self.client = MongoClient("mongodb+srv://kushalrdev:kush123@cluster0.hko96.mongodb.net/")
        self.db = self.client["medtrack"]

    def get_collection(self, name):
        return self.db[name]