from flask import Flask, request, jsonify, render_template
import smtplib, time, threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
import os
import queue
import ssl

app = Flask(__name__)

# =========================
# CONFIG
# =========================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_PORT_TLS = 587  # fallback port

SENDER_EMAIL = "grant.gov.support@gmail.com"
SENDER_PASSWORD = "wsppvssqffvqeaxa"
LOG_FILE = "smtp_web_log.log"

SEND_DELAY = 0.1  # ⚡ 10x faster (near instant)

MAX_RETRIES = 3
WORKER_THREADS = 20  # ⚡ more parallel sending
SMTP_TIMEOUT = 15  # ⚡ faster timeout

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
email_queue = queue.Queue()

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

    retries = 0

    while retries < MAX_RETRIES:
        try:
            context = ssl.create_default_context()

            # Try SSL (465)
            with smtplib.SMTP_SSL(
                SMTP_SERVER,
                SMTP_PORT,
                timeout=SMTP_TIMEOUT,
                context=context
            ) as server:

                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.sendmail(
                    SENDER_EMAIL,
                    to_email,
                    message.as_string()
                )

            logging.info(f"✅ Email sent to {to_email}")
            return True

        except Exception as ssl_error:

            try:
                # Fallback TLS (587)
                with smtplib.SMTP(
                    SMTP_SERVER,
                    SMTP_PORT_TLS,
                    timeout=SMTP_TIMEOUT
                ) as server:

                    server.starttls()
                    server.login(SENDER_EMAIL, SENDER_PASSWORD)

                    server.sendmail(
                        SENDER_EMAIL,
                        to_email,
                        message.as_string()
                    )

                logging.info(f"✅ Email sent (TLS) to {to_email}")
                return True

            except Exception as tls_error:
                retries += 1
                logging.warning(
                    f"⚠️ Retry {retries}/{MAX_RETRIES} for {to_email} | "
                    f"SSL Error: {ssl_error} | TLS Error: {tls_error}"
                )
                time.sleep(0.5)  # ⚡ faster retry

    logging.error(f"❌ Failed to send to {to_email} after retries")
    return False

# =========================
# WORKER THREAD
# =========================
def email_worker():
    while True:
        try:
            to_email, subject, plain_text, html_text = email_queue.get()

            send_email_now(
                to_email,
                subject,
                plain_text,
                html_text
            )

            email_queue.task_done()
            time.sleep(SEND_DELAY)

        except Exception as e:
            logging.error(f"Worker error: {e}")

# =========================
# START WORKERS
# =========================
for _ in range(WORKER_THREADS):
    threading.Thread(
        target=email_worker,
        daemon=True
    ).start()

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

    email_queue.put((
        to_email,
        subject,
        plain_text,
        html_text
    ))

    logging.info(f"📥 Queued email to {to_email}")

    return jsonify({
        "success": True,
        "message": f"Email queued for {to_email}"
    })

# =========================
# START APP
# =========================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
