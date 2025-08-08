from flask import Flask, request, jsonify, render_template
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

app = Flask(__name__)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = "plievnikiforradislavovich58@gmail.com"
SENDER_PASSWORD = "yqcqtpnmbxgbajav"
LOG_FILE = "smtp_web_log.log"

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)

@app.route('/')
def index():
    return render_template("form.html")

@app.route('/send-email', methods=['POST'])
def send_email():
    data = request.form
    to_emails_raw = data.get('to_email', '')
    subject = data.get('subject', '')
    plain_text = data.get('plain_text', '')
    html_text = data.get('html_text', '')

    # Split emails by comma or newline, and clean them
    to_emails = [email.strip() for email in to_emails_raw.replace('\n', ',').split(',') if email.strip()]
    
    # Setup mail server
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            
            for to_email in to_emails:
                message = MIMEMultipart("alternative")
                message["From"] = SENDER_EMAIL
                message["To"] = to_email
                message["Subject"] = subject
                message["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S")
                message.attach(MIMEText(plain_text, "plain"))

                if html_text:
                    message.attach(MIMEText(html_text, "html"))

                try:
                    server.sendmail(SENDER_EMAIL, to_email, message.as_string())
                    logging.info(f"✅ Email sent to {to_email}")
                except Exception as inner_e:
                    logging.error(f"❌ Failed to send to {to_email}: {inner_e}")

        return jsonify({"success": True, "message": f"Emails attempted to {len(to_emails)} recipient(s). Check log."})
    
    except Exception as e:
        logging.error(f"❌ Connection/login error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
