from flask import Flask, request, jsonify, render_template
import smtplib, time, threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
import os  # ✅ Import os here

app = Flask(__name__)

# =========================
# CONFIG
# =========================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = "plievnikiforradislavovich490@gmail.com"
SENDER_PASSWORD = "hynsicenemqaumyd"
LOG_FILE = "smtp_web_log.log"
SEND_DELAY = 10  # seconds between emails

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)

# =========================
# EMAIL QUEUE
# =========================
email_queue = []  # Each item: (to_email, subject, plain_text, html_text)

# =========================
# EMAIL SENDER
# =========================
def send_email_now(to_email, subject, plain_text, html_text):
    message = MIMEMultipart("alternative")
    message["From"] = SENDER_EMAIL
    message["To"] = to_email
    message["Subject"] = subject
    message["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S")
    message.attach(MIMEText(plain_text, "plain"))

    if html_text:
        message.attach(MIMEText(html_text, "html"))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, message.as_string())
        logging.info(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        logging.error(f"❌ Failed to send to {to_email}: {e}")
        return False

# =========================
# BACKGROUND SENDER LOOP
# =========================
def email_sender_loop():
    while True:
        if email_queue:
            to_email, subject, plain_text, html_text = email_queue.pop(0)
            send_email_now(to_email, subject, plain_text, html_text)
            time.sleep(SEND_DELAY)
        else:
            time.sleep(1)  # no emails, check again later

threading.Thread(target=email_sender_loop, daemon=True).start()

# =========================
# ROUTES
# =========================
@app.route('/')
def index():
    return render_template("form.html")

@app.route('/send-email', methods=['POST'])
def queue_email():
    data = request.form
    to_email = data.get('to_email')
    subject = data.get('subject')
    plain_text = data.get('plain_text')
    html_text = data.get('html_text')

    email_queue.append((to_email, subject, plain_text, html_text))
    logging.info(f"📥 Queued email to {to_email}")
    return jsonify({"success": True, "message": f"Email queued for {to_email}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
