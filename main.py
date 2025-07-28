import requests
import firebase_admin
from firebase_admin import credentials, firestore
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote

# Firebase setup
cred = credentials.Certificate("serviceaccountkey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

EMAIL = "recallohelp@gmail.com"
PASSWORD = "sevg yzhl pbwq emos"
HEADER_IMAGE_URL = "https://imgur.com/a/K58hrfM" 

def send_email(to, subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = to

    part = MIMEText(html_body, "html")
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)

def generate_email_html(state, recalls):
    rows = ""
    for recall in recalls:
        rows += f"""
        <tr>
            <td style="padding: 12px; border: 1px solid #ddd;">{recall['med']}</td>
            <td style="padding: 12px; border: 1px solid #ddd;">{recall['firm']}</td>
            <td style="padding: 12px; border: 1px solid #ddd;">{recall['location']}</td>
            <td style="padding: 12px; border: 1px solid #ddd;">{recall['reason']}</td>
            <td style="padding: 12px; border: 1px solid #ddd;">
                <a href="{recall['link']}" target="_blank">View</a>
            </td>
        </tr>
        """

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <div style="text-align: center; padding: 20px;">
            <img src="{HEADER_IMAGE_URL}" alt="Recallo Banner" style="max-width: 100%; height: auto;" />
            <h2 style="color: #2E86C1;">New Drug Recall(s) in Your State</h2>
            <p>Here are the latest recall notices for your prescriptions in <strong>{state}</strong>.</p>
        </div>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead style="background-color: #f2f2f2;">
                <tr>
                    <th style="padding: 12px; border: 1px solid #ddd;">Medication</th>
                    <th style="padding: 12px; border: 1px solid #ddd;">Firm</th>
                    <th style="padding: 12px; border: 1px solid #ddd;">Location</th>
                    <th style="padding: 12px; border: 1px solid #ddd;">Reason</th>
                    <th style="padding: 12px; border: 1px solid #ddd;">Details</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        <p style="text-align: center; margin-top: 30px;">Stay safe,<br><strong>The Recallo Team</strong></p>
    </body>
    </html>
    """

def check_recalls():
    users = db.collection("users").stream()

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
                        location = ", ".join(filter(None, [city, f"ZIP {zip_code}"])) or "Unknown"
                        openfda_link = f"https://open.fda.gov/drug/enforcement/#recall-{recall_number}"

                        new_recalls.append({
                            "med": med,
                            "firm": firm,
                            "location": location,
                            "reason": reason,
                            "link": openfda_link
                        })

                        sent_ref.set({"timestamp": firestore.SERVER_TIMESTAMP})

            except Exception as e:
                print(f"Error checking {med}: {e}")

        if new_recalls:
            html_body = generate_email_html(state, new_recalls)
            send_email(email, "New Drug Recall(s) in Your State", html_body)

check_recalls()
print("Everything is working fine")
