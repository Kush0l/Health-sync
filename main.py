from prettytable import PrettyTable
from datetime import datetime
from app.database import Database
from app.user import User
from app.prescription import Prescription


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

    def delete_prescription(self, doctor_id):
        """Handle prescription deletion flow"""
        patient_email = input("Enter patient email: ").strip().lower()

        # Find patient
        db = Database()
        user_manager = User(db)
        patient = user_manager.collection.find_one(
            {"email": patient_email, "role": "patient"})

        if not patient:
            print("Patient not found!")
            return

        # Get prescriptions
        prescriptions = self.prescription.get_for_patient(str(patient["_id"]))
        if not prescriptions:
            print("\nNo prescriptions found for this patient!")
            return

        # Display prescriptions
        self.display_prescriptions(prescriptions)

        try:
            pres_num = int(
                input("\nEnter prescription number to delete: ")) - 1
            if pres_num < 0 or pres_num >= len(prescriptions):
                print("Invalid prescription number!")
                return

            prescription = prescriptions[pres_num]
            confirm = input(
                f"\nAre you sure you want to delete prescription from {prescription['created_at'].strftime('%Y-%m-%d')}? (y/n): ").lower()
            if confirm != 'y':
                print("Deletion cancelled.")
                return

            if self.prescription.delete_prescription(str(prescription["_id"])):
                print("\nPrescription deleted successfully!")
            else:
                print("\nFailed to delete prescription!")

        except ValueError:
            print("\nPlease enter a valid number!")
        except Exception as e:
            print(f"\nAn error occurred: {e}")

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
            print("4. Get Patient Health Analysis")
            print("5. Delete Prescription")
            print("6. Logout")

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
                patient_email = input("Enter patient email: ").strip()
                analysis = self.prescription.get_patient_health_analysis(
                    str(user["_id"]), patient_email)
                print("\n=== HEALTH ANALYSIS ===")
                print(analysis)
                print("=" * 30)

            elif choice == "5":
                self.delete_prescription(str(user["_id"]))
            elif choice == "6":
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
            print("4. Update Health Summary")
            print("5. Logout")

            choice = input("\nChoose option: ").strip()

            if choice == "1":
                self.view_prescriptions(user)
            elif choice == "2":
                self.mark_medicine_taken(user)
            elif choice == "3":
                self.view_medication_history(user)
            elif choice == "4":  # New option
                self.user.update_health_summary(str(user["_id"]))
            elif choice == "5":
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
        tracker = HealthTracker()
        tracker.run()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        print("\nThank you for using MedTrack! Goodbye.\n")
