import requests
import firebase_admin
from firebase_admin import credentials, firestore
import smtplib
from email.mime.text import MIMEText
from urllib.parse import quote

# Initialize Firebase
cred = credentials.Certificate("serviceaccountkey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Your Gmail credentials (for testing, use an app password)
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
    print(f"Checking user: {data}")  # NEW
    email = data.get("email")
    state = data.get("state", "").upper()
    meds = data.get("medications", [])

    if not email or not state or not meds:
      print("Skipping user due to missing email/state/medications")  # NEW
      continue

    new_recalls = []
    for med in meds:
      med_encoded = quote(med)
      url = f"https://api.fda.gov/drug/enforcement.json?search=product_description:{med_encoded}+AND+state:{state}&limit=1"
      print(f"Requesting: {url}")  # NEW

      try:
        response = requests.get(url)
        print(f"Status code: {response.status_code}")  # NEW
        if response.status_code == 200:
          results = response.json().get("results", [])
          if results:
            recall = results[0]
            new_recalls.append(
                f"{med} by {recall.get('recalling_firm', 'N/A')}:\n{recall.get('reason_for_recall', 'N/A')}\n"
            )
        else:
          print(f"API error for {med}: {response.text}")  # NEW
      except Exception as e:
        print(f"Error checking {med}: {e}")

    if new_recalls:
      body = "\n\n".join(new_recalls)
      print(f"Sending email to {email} with recalls:\n{body}")  # NEW
      send_email(
          email, "New Drug Recall(s) in Your State",
          f"Here are the latest recall notices for your prescriptions in {state}:\n\n{body}"
      )
    else:
      print(f"No new recalls found for {email}")  # NEW


check_recalls()
print("Everything is working fine")
