from flask import Flask, request, jsonify, render_template
import smtplib, time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
import os
import ssl

app = Flask(__name__)

# =========================
# CONFIG
# =========================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORTS = [465, 587, 25]  # dynamic port list
SENDER_EMAIL = "grant.gov.support@gmail.com"
SENDER_PASSWORD = "wsppvssqffvqeaxa"
LOG_FILE = "smtp_web_log.log"

SMTP_TIMEOUT = 10    # fast timeout
RETRY_DELAY = 0.5    # retry wait

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)

# =========================
# EMAIL SENDER FUNCTION
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

    while True:  # keep trying until email is sent
        for port in SMTP_PORTS:
            try:
                if port == 465:  # SSL
                    context = ssl.create_default_context()
                    with smtplib.SMTP_SSL(SMTP_SERVER, port, timeout=SMTP_TIMEOUT, context=context) as server:
                        server.login(SENDER_EMAIL, SENDER_PASSWORD)
                        server.sendmail(SENDER_EMAIL, to_email, message.as_string())
                else:  # TLS or plain SMTP
                    with smtplib.SMTP(SMTP_SERVER, port, timeout=SMTP_TIMEOUT) as server:
                        if port == 587:
                            server.starttls()
                        server.login(SENDER_EMAIL, SENDER_PASSWORD)
                        server.sendmail(SENDER_EMAIL, to_email, message.as_string())

                logging.info(f"✅ Email sent to {to_email} via port {port}")
                return True

            except Exception as e:
                logging.warning(f"⚠️ Failed on port {port} for {to_email}: {e} | Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)

# =========================
# ROUTES
# =========================
@app.route('/')
def index():
    return render_template("form.html")

@app.route('/send-email', methods=['POST'])
def send_email_route():
    data = request.form
    to_email = data.get('to_email')
    subject = data.get('subject')
    plain_text = data.get('plain_text')
    html_text = data.get('html_text')

    # Send immediately without queue
    success = send_email_now(to_email, subject, plain_text, html_text)

    return jsonify({
        "success": success,
        "message": f"Email sent to {to_email}" if success else f"Failed to send to {to_email}"
    })

# =========================
# START APP
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
