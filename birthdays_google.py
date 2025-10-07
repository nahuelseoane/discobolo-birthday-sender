import csv
import datetime
import mimetypes
import os.path
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from discobolo.config.config import (
    CREDENTIALS_PATH,
    EMAIL_PASSWORD,
    EMAIL_USER,
    GMAIL_FALLBACK_ID,
    GMAIL_GROUP_ID,
    SMTP_PORT,
    SMTP_SERVER,
    TOKEN_PATH,
)

SCOPES = ["https://www.googleapis.com/auth/contacts.readonly"]

LOG_PATH = Path(__file__).parent / "sent_birthdays.csv"


def already_sent(email, today=None):
    today = today or datetime.datetime.now().strftime("%Y-%m-%d")
    if not LOG_PATH.exists:
        return False

    with open(LOG_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["email"] == email and row["date"] == today:
                return True
    return False


def record_email_sending(name, email, today=None):
    today = today or datetime.date.today().isoformat()

    new = pd.DataFrame([{"name": name, "email": email, "date": today}])

    if LOG_PATH.exists():
        actual = pd.read_csv(LOG_PATH)
        actual = pd.concat([actual, new], ignore_index=True)
    else:
        actual = new

    actual.to_csv(LOG_PATH, index=False)


def list_available_groups(service):
    results = service.contactGroups().list(pageSize=100).execute()
    groups = results.get("contactGroups", [])

    print("📂 Grupos encontrados:")
    for group in groups:
        print(f"- {group['name']} (ID: {group['resourceName']})")


def obtain_resource_group_name(service, group_name, fallback_resource_name=None):
    results = service.contactGroups().list(pageSize=100).execute()
    groups = results.get("contactGroups", [])

    for group in groups:
        group_name_actual = group.get("name", "")
        if group_name_actual.strip().lower() == group_name.strip().lower():
            print(f"✅ Grupo encontrado: {group_name_actual}")
            return group["resourceName"]

        print(f"❌ Group name couldn't be found: {group_name}")

        if fallback_resource_name:
            print(f"➡️ Usando fallback resourceName: {fallback_resource_name}")
            return fallback_resource_name
        return None


## 1
def authenticate():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(
                port=8080, access_type="offline", prompt="consent"
            )

        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
    return creds


## 2
def obtain_birthday(creds):
    service = build("people", "v1", credentials=creds)
    # list_available_groups(service)
    contact_group_id = obtain_resource_group_name(
        service, GMAIL_GROUP_ID, fallback_resource_name=GMAIL_FALLBACK_ID
    )

    results = (
        service.people()
        .connections()
        .list(
            resourceName="people/me",
            pageSize=2000,
            personFields="names,birthdays,emailAddresses,memberships",
        )
        .execute()
    )

    birthdays = []

    for person in results.get("connections", []):
        groups = person.get("memberships", [])

        belong = any(
            g.get("contactGroupMembership", {}).get("contactGroupResourceName")
            == contact_group_id
            for g in groups
        )

        if not belong:
            continue

        name = person.get("names", [{}])[0].get("displayName")
        email = person.get("emailAddresses", [{}])[0].get("value")
        cumple = person.get("birthdays", [{}])[0].get("date")

        if name and email and cumple:
            mes_dia = f"{cumple.get('month'):02d}-{cumple.get('day'):02d}"
            hoy = datetime.datetime.today().strftime("%m-%d")
            if mes_dia == hoy:
                birthdays.append((name, email))

    return birthdays


def send_email(addressee, name, image_path):
    msg = EmailMessage()
    msg["Subject"] = f"🎉 ¡Feliz Cumple {name}!"
    msg["From"] = EMAIL_USER
    msg["To"] = addressee

    image_cid = make_msgid(domain="discobolo.club")
    image_cid_stripped = image_cid[1:-1]

    msg.set_content(f"""
        Hola {name} 👋
        
        
        🎂 ¡El Club Discóbolo te desea un muy feliz cumpleaños!

        Que tengas un gran día lleno de alegría y buenos momentos 🎾🎈

        ¡Te esperamos para celebrarlo en el club!

        Saludos,
        Club Discóbolo
        """)

    msg.add_alternative(
        f"""
        <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <p>Hola {name} 👋🎉</p>
                    <br>
                    <p>¡El <strong>Club Discobolo</strong> te desea un muy feliz cumpleaños!🎂</p>
                    <div style="text-align: center; margin: 25px 0;">
                        <img src="cid:{image_cid_stripped}" alt="Feliz cumple" style="width:65%; max-width:360px; border-radius:16px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);"/>
                    </div>
                    <p>¡Te esperamos para celebrarlo en el club! 🎾🥳</p>
                    <br>
                    <p>Saludos,</p>
                    <p style="font-size: 0.9em; color #888;">Club de Deportes Discobolo</p>
                </body>
        </html>
        """,
        subtype="html",
    )

    mime_type, _ = mimetypes.guess_type(image_path)
    maintype, subtype = mime_type.split("/")

    with open(image_path, "rb") as img:
        msg.get_payload()[1].add_related(
            img.read(), maintype=maintype, subtype=subtype, cid=image_cid
        )

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASSWORD)
        smtp.send_message(msg)

    print(f"📧 Email enviado a {name} ({addressee})")


## 3
def run_birthday_emails():
    creds = authenticate()
    birthdays = obtain_birthday(creds)

    if birthdays:
        for name, email in birthdays:
            if already_sent(email):
                print(f"⏭️ Ya se envió el email a {name}, se omite.")
                continue
            print(f"🎉 Hoy cumple {name} ({email})")
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(BASE_DIR, "card_last.png")
            send_email(email, name, image_path)
            record_email_sending(name, email)

    else:
        print("📭 Hoy no cumple nadie (según tus contactos).")


if __name__ == "__main__":
    run_birthday_emails()
