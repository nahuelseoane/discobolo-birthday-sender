# 📨🎂 Discobbolo Birthday Sender

Automates daily **birthday greetings** for ***Club de Deportes Discobolo***. If feteches today's birthdays from a Google Contacts group and sends personalized HTML emails (with an embedded image) either locally or via **GitHub Actions** every morning at 09:00 (Argentina).

## ✨ Features
- Reads members from a Google Contacts group ( GMAIL_GROUP_ID ), with optional fallback **resourceName**.
- Sends a friendly **HTML email** with the card image *card_last.png* embedded inline.
- **Idempotent**: records each send in *sent_birthdays.csv* (Google Sheets)
- Runs headlessly in the cloud with **GitHub Actionis** on a daily schedule.

## 📷 Screenshot
![Screenshot of Discobolo-birthday-sender](https://i.imgur.com/fbxpxmE.png)

## 📂 File Structure

```
/
├── .github/workflows/birthdays.yml        # CI workflow (daily)
├── birthdays_google.py                    # main script (auth, fetch People, send email)
├── config.py                              # env-based configuration
├── requirements.txt
└── README.md
```

## 🧑‍💻 Author
**Nahuel Seoane** - [@nahuelseoane](https://github.com/nahuelseoane)
Built as part of the Automating Discobolo project.
