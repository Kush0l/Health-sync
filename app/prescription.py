from datetime import datetime, time
from bson import ObjectId
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import Database
from app.user import User
from app.email_service import EmailService


class Prescription:
    def __init__(self, db):
        self.collection = db.get_collection("prescriptions")
        self.medication_records = db.get_collection("medication_records")
        self.scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
        self.email_service = EmailService()
        self.scheduler.add_job(self.reset_daily_status,
                               'cron', hour=0, minute=0)
        self._reschedule_existing_prescriptions()  # Add this line

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

    def schedule_medication_reminders(self, prescription):
        """Schedule email reminders for each medicine"""
        try:
            patient_id = prescription["patient_id"]
            db = Database()
            user = User(db)
            patient = user.collection.find_one({"_id": ObjectId(patient_id)})

            if not patient:
                print(
                    f"Patient not found for prescription {prescription['_id']}")
                return

            for medicine in prescription["medicines"]:
                times = [t.strip() for t in medicine["time"].split(",")]

                for time_of_day in times:
                    cron_schedule = self._get_cron_schedule(time_of_day)
                    if not cron_schedule:
                        continue

                    self.scheduler.add_job(
                        self._send_reminder_email,
                        CronTrigger(
                            hour=cron_schedule["hour"],
                            minute=cron_schedule["minute"],
                            timezone="Asia/Kolkata"
                        ),
                        args=[
                            patient["email"],
                            medicine["name"],
                            medicine["dosage"],
                            time_of_day
                        ],
                        id=f"reminder_{prescription['_id']}_{medicine['name']}_{time_of_day}",
                        replace_existing=True
                    )

                    print(
                        f"Scheduled {medicine['name']} reminder for {time_of_day}")

        except Exception as e:
            print(f"Error scheduling reminders: {e}")

    def _get_cron_schedule(self, time_of_day):
        """Convert human-readable times to cron schedule"""
        time_mapping = {
            "morning": {"hour": 9, "minute": 0},
            "afternoon": {"hour": 13, "minute": 0},
            "evening": {"hour": 18, "minute": 0},
            "night": {"hour": 19, "minute": 34}
        }
        return time_mapping.get(time_of_day.lower())

    def _send_reminder_email(self, patient_email, medicine_name, dosage, time_of_day):
        """Send a reminder email"""
        print(
            f"Sending reminder for {medicine_name} at {time_of_day} to {patient_email}")
        return self.email_service.send_medication_reminder(
            patient_email, medicine_name, dosage, time_of_day
        )

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

            # Schedule reminders for the new prescription
            self.schedule_medication_reminders(prescription)

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

    def _reschedule_existing_prescriptions(self):
        """Reload all prescriptions and reschedule on server start"""
        prescriptions = self.collection.find({})
        for pres in prescriptions:
            self.schedule_medication_reminders(pres)

    def get_patient_health_analysis(self, doctor_id, patient_email):
        """Get patient health analysis with Gemini"""
        try:
            db = Database()
            user = User(db)
            
            # Get patient
            patient = user.collection.find_one({"email": patient_email, "role": "patient"})
            if not patient:
                return "Patient not found"
            
            # Get prescriptions
            prescriptions = self.get_for_patient(str(patient["_id"]))
            pres_data = [{
                "medicines": [m["name"] for m in p["medicines"]],
                "notes": p["notes"],
                "created_at": p["created_at"]
            } for p in prescriptions]
            
            # Get analysis
            return user.get_health_analysis(str(patient["_id"]), pres_data)
        except Exception as e:
            print(f"Error getting health analysis: {e}")
            return "Could not generate analysis"