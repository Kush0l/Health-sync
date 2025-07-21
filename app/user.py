import bcrypt
import getpass
from datetime import datetime
from app.gemini_service import GeminiService
from bson import ObjectId



class User:
    def __init__(self, db):
        self.collection = db.get_collection("users")
        self.gemini = GeminiService()

    def register(self):
        print("\n--- Register ---")
        name = input("Name: ").strip()
        email = input("Email: ").strip().lower()

        if "@" not in email or "." not in email:
            print("Invalid email format!")
            return None

        if self.collection.find_one({"email": email}):
            print("Email already exists!")
            return None

        password = getpass.getpass("Password: ")
        if len(password) < 6:
            print("Password must be at least 6 characters!")
            return None

        role = input("Role (doctor/patient): ").strip().lower()
        if role not in ["doctor", "patient"]:
            print("Role must be 'doctor' or 'patient'")
            return None

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        user = {
            "name": name,
            "email": email,
            "password": hashed,
            "role": role,
            "created_at": datetime.now(),
            "timezone": "UTC"
        }

        try:
            user_id = self.collection.insert_one(user).inserted_id
            print(f"\nUser registered successfully! ID: {user_id}")
            return str(user_id)
        except Exception as e:
            print(f"Registration failed: {e}")
            return None

    def login(self):
        print("\n--- Login ---")
        email = input("Email: ").strip().lower()
        password = getpass.getpass("Password: ")

        try:
            user = self.collection.find_one({"email": email})
            if not user or not bcrypt.checkpw(password.encode(), user["password"]):
                print("Invalid credentials!")
                return None

            print(f"\nWelcome {user['name']} ({user['role']})!")
            return user
        except Exception as e:
            print(f"Login failed: {e}")
            return None
    
    def update_health_summary(self, user_id):
        user = self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            print("User not found!")
            return False

        print("\n--- Update Health Summary ---")
        print("Current summary:", user.get("health_summary", "None"))
        
        new_summary = input("\nEnter your health summary (or press enter to keep current): ").strip()
        if not new_summary:
            return True  

        try:
            result = self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"health_summary": new_summary}}
            )
            
            if result.modified_count > 0:
                print("\nHealth summary updated successfully!")
                return True
            return False
        except Exception as e:
            print(f"Error updating health summary: {e}")
            return False

    def get_health_analysis(self, user_id, prescriptions):
        user = self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return "Patient not found"

        health_summary = user.get("health_summary", "No health summary provided")
        return self.gemini.analyze_health_summary(health_summary, prescriptions)