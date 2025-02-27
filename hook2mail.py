from flask import Flask, request, jsonify
import smtplib
from email.message import EmailMessage
from email.parser import Parser
import os
import base64

EMAIL_FROM = os.getenv("EMAIL_FROM", "meetups@cloudnative.aixmarseille.tech")
EMAIL_TO = os.getenv("EMAIL_TO", "contact@webofmars.com, another@example.com, third@example.com")
PORT = int(os.getenv("PORT", 8000))

SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", 1025))
USE_STARTTLS = os.getenv("USE_STARTTLS", "false").lower() == "true"
USE_LOGIN = os.getenv("USE_LOGIN", "false").lower() == "true"
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        message_base64 = data.get('message', '')
        raw_message = base64.b64decode(message_base64).decode('utf-8')
        email_message = Parser().parsestr(raw_message)

        # Extract the original sender
        original_sender = email_message.get('From', 'Unknown Sender')

        payload = None
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    break
        else:
            payload = email_message.get_payload(decode=True)

        if payload is None:
            raise ValueError("The email body is missing or not decodable")

        message_content = payload.decode('utf-8')
        if len(message_content) < 10:
            raise ValueError("The email body must have at least 10 characters")

        send_email(message_content, original_sender)
        return "OK", 200
    except (KeyError, ValueError, base64.binascii.Error) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def send_email(content, original_sender):
    msg = EmailMessage()
    msg.set_content(content)
    msg["Subject"] = f"Forwarded email from {original_sender}"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        if USE_STARTTLS:
            server.starttls()
        if USE_LOGIN:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
