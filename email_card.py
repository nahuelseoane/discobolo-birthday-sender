import smtplib
from email.message import EmailMessage


def enviar_email(destinatario, nombre, imagen_path):
    msg = EmailMessage()
    msg["Subject"] = f"¡Feliz Cumple {nombre}!"
    msg["From"] = "tuemail@club.com"
    msg["To"] = destinatario
    msg.set_content(
        f"¡Hola {nombre}!\n\nEl Club Discóbolo te desea un muy feliz cumpleaños 🎉")

    with open(imagen_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="image",
                           subtype="jpeg", filename="feliz_cumple.jpg")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login("tuemail@club.com", "tu_contraseña")
        smtp.send_message(msg)
