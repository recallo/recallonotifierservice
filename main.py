import requests
import firebase_admin
from firebase_admin import credentials, firestore
import smtplib
from email.mime.text import MIMEText
from urllib.parse import quote


cred = credentials.Certificate("serviceaccountkey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

EMAIL = "recallohelp@gmail.com"
PASSWORD = "sevg yzhl pbwq emos"


def send_email(to, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)


def check_recalls():
    users_ref = db.collection("users")
    users = users_ref.stream()

    for user in users:
        data = user.to_dict()
        email = data.get("email")
        state = data.get("state", "").upper()
        meds = data.get("medications", [])
        user_id = user.id

        if not email or not state or not meds:
            continue

        new_recalls = []

        for med in meds:
            med_encoded = quote(med)
            url = f"https://api.fda.gov/drug/enforcement.json?search=product_description:{med_encoded}+AND+state:{state}&limit=1"

            try:
                response = requests.get(url)
                if response.status_code == 200:
                    results = response.json().get("results", [])
                    if results:
                        recall = results[0]
                        recall_number = recall.get("recall_number")
                        if not recall_number:
                            continue

                        sent_ref = db.collection("users").document(user_id).collection("sent_recalls").document(recall_number)
                        if sent_ref.get().exists:
                            continue

                        firm = recall.get("recalling_firm", "N/A")
                        reason = recall.get("reason_for_recall", "N/A")
                        city = recall.get("city", "")
                        zip_code = recall.get("postal_code", "")
                        location = ""

                        if city and zip_code:
                            location = f"{city}, ZIP {zip_code}"
                        elif city:
                            location = city
                        elif zip_code:
                            location = f"ZIP {zip_code}"
                        else:
                            location = "Unknown location"

                        message = f"{med} by {firm} ({location}):\n{reason}"
                        new_recalls.append(message)

                       
                        sent_ref.set({"timestamp": firestore.SERVER_TIMESTAMP})
                else:
                    print(f"API error for {med}: {response.text}")
            except Exception as e:
                print(f"Error checking {med}: {e}")

        if new_recalls:
            body = "\n\n".join(new_recalls)
            send_email(
                email,
                "New Drug Recall(s) in Your State",
                f"Here are the latest recall notices for your prescriptions in {state}:\n\n{body}"
            )


check_recalls()
print("Everything is working fine")
