from pymongo import MongoClient
from datetime import datetime, timedelta
import bcrypt
import getpass
from bson import ObjectId
from prettytable import PrettyTable
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

# Database Setup


class Database:
    def __init__(self):
        self.client = MongoClient(
            "mongodb+srv://afwan8334:Ctu087351@cluster0.tewsas4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
        self.db = self.client["medtrack"]

    def get_collection(self, name):
        return self.db[name]

# User Management


class User:
    def __init__(self, db):
        self.collection = db.get_collection("users")

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

# Prescription Management


class Prescription:
    def __init__(self, db):
        self.collection = db.get_collection("prescriptions")
        self.medication_records = db.get_collection("medication_records")
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self.scheduler.add_job(self.reset_daily_status,
                               'cron', hour=0, minute=0)  # Midnight reset
        self.scheduler.start()

    def reset_daily_status(self):
        """Reset all 'taken' statuses at midnight"""
        try:
            result = self.collection.update_many(
                {},
                {"$set": {"medicines.$[].taken_today": False}}
            )
            print(f"\nReset {result.modified_count} prescriptions for new day")
        except Exception as e:
            print(f"Error resetting statuses: {e}")

    def create(self, doctor_id):
        print("\n--- New Prescription ---")
        patient_email = input("Patient email: ").strip().lower()

        db = Database()
        user = User(db)
        patient = user.collection.find_one(
            {"email": patient_email, "role": "patient"})

        if not patient:
            print("Patient not found!")
            return None

        medicines = []
        while True:
            print("\nAdd Medicine:")
            name = input("Name: ").strip()
            if not name:
                print("Medicine name cannot be empty!")
                continue

            dosage = input("Dosage: ").strip()
            frequency = input("Frequency: ").strip()
            time_input = input(
                "Time (comma separated, e.g., morning,afternoon,night): ").strip()

            times = [t.strip() for t in time_input.split(",") if t.strip()]
            if not times:
                print("At least one time must be specified!")
                continue

            medicines.append({
                "name": name,
                "dosage": dosage,
                "frequency": frequency,
                "time": ", ".join(times),
                "taken_today": False,
                "last_taken": None,
                "total_taken": 0
            })

            if input("\nAdd another medicine? (y/n): ").lower() != 'y':
                break

        notes = input("\nNotes: ").strip()

        prescription = {
            "doctor_id": doctor_id,
            "patient_id": str(patient["_id"]),
            "medicines": medicines,
            "notes": notes,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        try:
            pres_id = self.collection.insert_one(prescription).inserted_id
            print(f"\nPrescription created successfully! ID: {pres_id}")
            return str(pres_id)
        except Exception as e:
            print(f"Failed to create prescription: {e}")
            return None

    def get_for_patient(self, patient_id):
        try:
            return list(self.collection.find({"patient_id": patient_id}).sort("created_at", -1))
        except Exception as e:
            print(f"Error fetching prescriptions: {e}")
            return []

    def mark_medicine_taken(self, prescription_id, med_index):
        try:
            prescription = self.collection.find_one(
                {"_id": ObjectId(prescription_id)})
            if not prescription:
                print("Prescription not found!")
                return False

            medicine = prescription["medicines"][med_index]

            # Initialize missing fields
            if "taken_today" not in medicine:
                medicine["taken_today"] = False
            if "total_taken" not in medicine:
                medicine["total_taken"] = 0

            if medicine["taken_today"]:
                last_taken = medicine["last_taken"].strftime(
                    "%H:%M") if medicine.get("last_taken") else "previously"
                print(
                    f"\n{medicine['name']} was already marked as taken today at {last_taken}!")
                return False

            update_result = self.collection.update_one(
                {"_id": ObjectId(prescription_id)},
                {
                    "$set": {
                        f"medicines.{med_index}.taken_today": True,
                        f"medicines.{med_index}.last_taken": datetime.now(),
                        "updated_at": datetime.now()
                    },
                    "$inc": {f"medicines.{med_index}.total_taken": 1}
                }
            )

            if update_result.modified_count == 0:
                print("Failed to update prescription!")
                return False

            record = {
                "prescription_id": prescription_id,
                "medicine_name": medicine["name"],
                "dosage": medicine["dosage"],
                "time_taken": datetime.now(),
                "patient_id": prescription["patient_id"],
                "doctor_id": prescription["doctor_id"]
            }

            self.medication_records.insert_one(record)
            return True

        except Exception as e:
            print(f"Error marking medicine: {e}")
            return False

    def get_medication_history(self, patient_id):
        """Get complete medication history for a patient"""
        try:
            return list(self.medication_records.find(
                {"patient_id": patient_id}
            ).sort("time_taken", -1))
        except Exception as e:
            print(f"Error fetching medication history: {e}")
            return []

    def get_patient_records(self, doctor_id):
        """Get all patient records for a doctor"""
        try:
            prescriptions = list(self.collection.find(
                {"doctor_id": doctor_id}
            ).sort("created_at", -1))

            patient_records = {}
            for pres in prescriptions:
                patient_id = pres["patient_id"]
                if patient_id not in patient_records:
                    db = Database()
                    user = User(db)
                    patient = user.collection.find_one(
                        {"_id": ObjectId(patient_id)})
                    if not patient:
                        continue

                    patient_records[patient_id] = {
                        "patient_info": {
                            "name": patient["name"],
                            "email": patient["email"],
                            "join_date": patient["created_at"]
                        },
                        "prescriptions": []
                    }
                patient_records[patient_id]["prescriptions"].append(pres)

            return patient_records
        except Exception as e:
            print(f"Error fetching patient records: {e}")
            return {}

# Main Application


class HealthTracker:
    def __init__(self):
        self.db = Database()
        self.user = User(self.db)
        self.prescription = Prescription(self.db)

    def display_prescriptions(self, prescriptions):
        if not prescriptions:
            print("\nNo prescriptions found!")
            return

        for i, pres in enumerate(prescriptions):
            table = PrettyTable()
            table.title = f"Prescription {i+1} (Created: {pres['created_at'].strftime('%Y-%m-%d')})"
            table.field_names = ["#", "Medicine", "Dosage",
                                 "Frequency", "Time", "Today", "Last Taken", "Total Taken"]

            for j, med in enumerate(pres["medicines"]):
                today_status = "✓" if med.get("taken_today", False) else "✗"
                last_taken = med.get("last_taken", "").strftime(
                    "%m-%d %H:%M") if med.get("last_taken") else "Never"
                total_taken = med.get("total_taken", 0)
                table.add_row([
                    j+1,
                    med["name"],
                    med["dosage"],
                    med["frequency"],
                    med["time"],
                    today_status,
                    last_taken,
                    total_taken
                ])

            print(f"\nDoctor's Notes: {pres['notes']}")
            print(table)

    def view_medication_history(self, user):
        history = self.prescription.get_medication_history(str(user["_id"]))

        if not history:
            print("\nNo medication history found!")
            return

        table = PrettyTable()
        table.title = "Your Medication History"
        table.field_names = ["Date", "Medicine", "Dosage", "Time Taken"]

        for record in history:
            table.add_row([
                record["time_taken"].strftime("%Y-%m-%d"),
                record["medicine_name"],
                record["dosage"],
                record["time_taken"].strftime("%H:%M")
            ])

        print(f"\nTotal medications taken: {len(history)}")
        print(table)

    def view_patient_records(self, user):
        records = self.prescription.get_patient_records(str(user["_id"]))

        if not records:
            print("\nNo patient records found!")
            return

        for patient_id, data in records.items():
            patient = data["patient_info"]
            print(f"\nPatient: {patient['name']} ({patient['email']})")
            print(f"Member since: {patient['join_date'].strftime('%Y-%m-%d')}")
            print(f"Total prescriptions: {len(data['prescriptions'])}")

            table = PrettyTable()
            table.title = "Recent Prescriptions"
            table.field_names = ["Date", "Medicines", "Last Updated"]

            for pres in data["prescriptions"][:3]:
                med_names = ", ".join([m["name"] for m in pres["medicines"]])
                table.add_row([
                    pres["created_at"].strftime("%Y-%m-%d"),
                    med_names,
                    pres["updated_at"].strftime("%Y-%m-%d %H:%M")
                ])

            print(table)

    def run(self):
        print("\n" + "="*50)
        print("MEDTRACK - Medication Management System")
        print("="*50)

        while True:
            print("\nMain Menu:")
            print("1. Register")
            print("2. Login")
            print("3. Exit")

            choice = input("\nChoose option: ").strip()

            if choice == "1":
                self.user.register()
            elif choice == "2":
                user = self.user.login()
                if user:
                    self.user_menu(user)
            elif choice == "3":
                break
            else:
                print("Invalid choice! Please enter 1, 2, or 3.")

    def user_menu(self, user):
        if user["role"] == "doctor":
            self.doctor_menu(user)
        else:
            self.patient_menu(user)

    def doctor_menu(self, user):
        while True:
            print("\n" + "="*50)
            print(f"DOCTOR MENU - Welcome Dr. {user['name']}")
            print("1. Create New Prescription")
            print("2. View Patient Records")
            print("3. View Patient Medication History")
            print("4. Logout")

            choice = input("\nChoose option: ").strip()

            if choice == "1":
                self.prescription.create(str(user["_id"]))
            elif choice == "2":
                self.view_patient_records(user)
            elif choice == "3":
                patient_email = input("Enter patient email: ").strip()
                db = Database()
                user_manager = User(db)
                patient = user_manager.collection.find_one(
                    {"email": patient_email, "role": "patient"})
                if patient:
                    self.view_medication_history(patient)
                else:
                    print("Patient not found!")
            elif choice == "4":
                print("\nLogging out...")
                break
            else:
                print("Invalid choice!")

    def patient_menu(self, user):
        while True:
            print("\n" + "="*50)
            print(f"PATIENT MENU - Welcome {user['name']}")
            print("1. View My Prescriptions")
            print("2. Mark Medicine as Taken")
            print("3. View My Medication History")
            print("4. Logout")

            choice = input("\nChoose option: ").strip()

            if choice == "1":
                self.view_prescriptions(user)
            elif choice == "2":
                self.mark_medicine_taken(user)
            elif choice == "3":
                self.view_medication_history(user)
            elif choice == "4":
                print("\nLogging out...")
                break
            else:
                print("Invalid choice!")

    def view_prescriptions(self, user):
        prescriptions = self.prescription.get_for_patient(str(user["_id"]))
        self.display_prescriptions(prescriptions)

    def mark_medicine_taken(self, user):
        prescriptions = self.prescription.get_for_patient(str(user["_id"]))

        if not prescriptions:
            print("\nNo prescriptions found!")
            return

        self.display_prescriptions(prescriptions)

        try:
            pres_num = int(input("\nEnter prescription number: ")) - 1
            if pres_num < 0 or pres_num >= len(prescriptions):
                print("Invalid prescription number!")
                return

            med_num = int(input("Enter medicine number: ")) - 1
            prescription = prescriptions[pres_num]

            if med_num < 0 or med_num >= len(prescription["medicines"]):
                print("Invalid medicine number!")
                return

            medicine = prescription["medicines"][med_num]

            confirm = input(
                f"\nMark {medicine['name']} ({medicine['dosage']}) as taken today? (y/n): ").lower()
            if confirm != 'y':
                print("Cancelled.")
                return

            if self.prescription.mark_medicine_taken(str(prescription["_id"]), med_num):
                print(
                    f"\nSuccessfully marked {medicine['name']} as taken at {datetime.now().strftime('%H:%M')}!")
                print(f"Total times taken: {medicine['total_taken'] + 1}")
            else:
                print("\nFailed to mark medicine!")

        except ValueError:
            print("\nPlease enter valid numbers!")
        except Exception as e:
            print(f"\nAn error occurred: {e}")


if __name__ == "__main__":
    try:
        # Run migration for existing data (uncomment first run)
        # db = Database()
        # prescriptions = db.get_collection("prescriptions")
        # prescriptions.update_many(
        #     {},
        #     {"$set": {
        #         "medicines.$[].taken_today": False,
        #         "medicines.$[].total_taken": 0
        #     }}
        # )

        tracker = HealthTracker()
        tracker.run()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        print("\nThank you for using MedTrack! Goodbye.\n")
