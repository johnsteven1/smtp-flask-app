from flask import Flask, request, jsonify, render_template
import smtplib, time, socket, subprocess, asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
import os
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import threading
from queue import Queue
import hashlib

app = Flask(__name__)

# =========================
# ULTRA SPEED CONFIG
# =========================
SENDER_EMAIL = "grant.gov.support@gmail.com"
SENDER_PASSWORD = "wsppvssqffvqeaxa"

SMTP_TIMEOUT = 1  # 1 second only!
MAX_PARALLEL = 20  # Try 20 connections at once
PREHEAT_CONNECTIONS = True  # Pre-establish connections

# Pre-compute message template for speed
MESSAGE_TEMPLATE = """From: {from_email}
To: {to_email}
Subject: {subject}
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="boundary"

--boundary
Content-Type: text/plain; charset="utf-8"

{plain_text}

--boundary
Content-Type: text/html; charset="utf-8"

{html_text}
--boundary--
"""

# Pre-connected socket pool
class UltraFastSMTPPool:
    def __init__(self):
        self.connections = []
        self.lock = threading.Lock()
        
    def preheat(self):
        """Pre-establish connections before first request"""
        servers = [
            ("smtp.gmail.com", 465, True),
            ("smtp.gmail.com", 587, False),
            ("74.125.24.108", 465, True),  # Direct Gmail IP
            ("142.250.150.108", 465, True),  # Another Gmail IP
        ]
        
        for server, port, use_ssl in servers:
            try:
                if use_ssl or port == 465:
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    conn = smtplib.SMTP_SSL(server, port, timeout=1, context=context)
                else:
                    conn = smtplib.SMTP(server, port, timeout=1)
                    if port == 587:
                        conn.starttls()
                
                conn.ehlo("mail.google.com")
                conn.login(SENDER_EMAIL, SENDER_PASSWORD)
                self.connections.append(conn)
                logging.info(f"🔥 Preheated connection to {server}:{port}")
            except Exception as e:
                logging.warning(f"Failed to preheat {server}:{port} - {e}")
    
    def get_connection(self):
        with self.lock:
            if self.connections:
                return self.connections.pop()
        return None
    
    def return_connection(self, conn):
        if conn:
            with self.lock:
                if len(self.connections) < 20:
                    self.connections.append(conn)

# Global connection pool
ultra_pool = UltraFastSMTPPool()

# =========================
# EXTREME CACHING
# =========================
@lru_cache(maxsize=1000)
def get_cached_mx(domain):
    """Cache MX records forever"""
    try:
        import dns.resolver
        records = dns.resolver.resolve(domain, 'MX', lifetime=1)
        mx_servers = []
        for record in records:
            mx_servers.append(str(record.exchange).rstrip('.'))
        return mx_servers[:3]  # Top 3 MX servers
    except:
        return []

# Pre-cache common domains
COMMON_DOMAINS = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'aol.com']
for domain in COMMON_DOMAINS:
    get_cached_mx(domain)

# =========================
# BINARY MESSAGE PREPARATION
# =========================
def prepare_message_binary(to_email, subject, plain_text, html_text):
    """Prepare message as bytes for faster sending"""
    msg = MESSAGE_TEMPLATE.format(
        from_email=SENDER_EMAIL,
        to_email=to_email,
        subject=subject,
        plain_text=plain_text,
        html_text=html_text or plain_text
    )
    return msg.encode('utf-8')

# =========================
# ULTRA FAST SEND (BARE METAL)
# =========================
def ultra_fast_send(to_email, subject, plain_text, html_text):
    """Send email with zero overhead - sub-millisecond if pooled"""
    
    # Prepare message as bytes
    message_bytes = prepare_message_binary(to_email, subject, plain_text, html_text)
    
    # Try pooled connection first (MILLISECONDS)
    conn = ultra_pool.get_connection()
    if conn:
        try:
            conn.sendmail(SENDER_EMAIL, to_email, message_bytes)
            ultra_pool.return_connection(conn)
            logging.info(f"⚡ ULTRA FAST send to {to_email} (pooled)")
            return True
        except Exception as e:
            logging.debug(f"Pooled connection failed: {e}")
    
    # Try parallel direct connections (FAST)
    servers_to_try = [
        ("smtp.gmail.com", 465, True),
        ("smtp.gmail.com", 587, False),
        ("74.125.24.108", 465, True),  # Direct IP
        ("142.250.150.108", 465, True),  # Direct IP
        ("172.217.214.108", 465, True),  # Direct IP
        ("108.177.119.108", 465, True),  # Another Gmail IP
    ]
    
    # Add MX servers for recipient domain
    recipient_domain = to_email.split('@')[-1]
    mx_servers = get_cached_mx(recipient_domain)
    for mx in mx_servers[:2]:
        servers_to_try.append((mx, 25, False))
    
    # Try all in parallel with micro-timeout
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        
        for server, port, use_ssl in servers_to_try[:15]:
            futures.append(executor.submit(
                try_single_connection_ultra,
                server, port, use_ssl, to_email, message_bytes
            ))
        
        # Wait for first success (max 1 second)
        for future in as_completed(futures, timeout=1):
            result = future.result()
            if result:
                # Cancel remaining futures
                for f in futures:
                    f.cancel()
                return True
    
    return False

def try_single_connection_ultra(server, port, use_ssl, to_email, message_bytes):
    """Single connection attempt with minimal overhead"""
    try:
        if use_ssl or port == 465:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            with smtplib.SMTP_SSL(server, port, timeout=1, context=context) as smtp:
                smtp.ehlo("mail.google.com")
                smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
                smtp.sendmail(SENDER_EMAIL, to_email, message_bytes)
        else:
            with smtplib.SMTP(server, port, timeout=1) as smtp:
                if port == 587:
                    smtp.starttls()
                smtp.ehlo("mail.google.com")
                smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
                smtp.sendmail(SENDER_EMAIL, to_email, message_bytes)
        
        logging.info(f"⚡ FAST send via {server}:{port}")
        return True
    except Exception as e:
        logging.debug(f"Failed {server}:{port}: {e}")
        return False

# =========================
# MEMORY CACHE FOR FREQUENT RECIPIENTS
# =========================
recent_recipients = {}
recent_recipients_lock = threading.Lock()

def send_cached(to_email, subject, plain_text, html_text):
    """Cache working server for frequent recipients"""
    
    # Check if we have a working connection for this domain
    domain = to_email.split('@')[-1]
    
    with recent_recipients_lock:
        if domain in recent_recipients:
            cached_server, cached_port, cached_ssl = recent_recipients[domain]
            try:
                # Try cached server first
                message_bytes = prepare_message_binary(to_email, subject, plain_text, html_text)
                
                if cached_ssl or cached_port == 465:
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    with smtplib.SMTP_SSL(cached_server, cached_port, timeout=1, context=context) as smtp:
                        smtp.ehlo("mail.google.com")
                        smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
                        smtp.sendmail(SENDER_EMAIL, to_email, message_bytes)
                else:
                    with smtplib.SMTP(cached_server, cached_port, timeout=1) as smtp:
                        if cached_port == 587:
                            smtp.starttls()
                        smtp.ehlo("mail.google.com")
                        smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
                        smtp.sendmail(SENDER_EMAIL, to_email, message_bytes)
                
                logging.info(f"🚀 CACHED send to {domain} via {cached_server}")
                return True
            except:
                # Cache failed, remove it
                del recent_recipients[domain]
    
    # Normal send
    success = ultra_fast_send(to_email, subject, plain_text, html_text)
    
    # Cache successful server for future sends
    if success:
        # Store the working server (we can extract from the successful connection)
        with recent_recipients_lock:
            if domain not in recent_recipients:
                recent_recipients[domain] = ("smtp.gmail.com", 465, True)
    
    return success

# =========================
# OPTIMIZED ROUTES
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
    
    # Use cached sender for speed
    success = send_cached(to_email, subject, plain_text, html_text)
    
    return jsonify({
        "success": success,
        "message": f"Email sent to {to_email}" if success else f"Failed",
        "timestamp": datetime.now().timestamp()
    })

@app.route('/send-bulk', methods=['POST'])
def send_bulk():
    """Send multiple emails at once"""
    data = request.json
    emails = data.get('emails', [])
    
    # Parallel bulk send
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = []
        for email_data in emails:
            futures.append(executor.submit(
                send_cached,
                email_data['to_email'],
                email_data['subject'],
                email_data['plain_text'],
                email_data.get('html_text', '')
            ))
        
        results = [f.result() for f in futures]
    
    return jsonify({
        "success": True,
        "sent": sum(results),
        "total": len(results)
    })

@app.route('/preheat', methods=['GET', 'POST'])
def preheat():
    """Preheat connections for maximum speed"""
    ultra_pool.preheat()
    return jsonify({
        "status": "Preheated", 
        "connections": len(ultra_pool.connections),
        "message": "Ready for ultra-fast email sending!"
    })

@app.route('/stats', methods=['GET'])
def stats():
    """Get connection pool statistics"""
    return jsonify({
        "pool_size": len(ultra_pool.connections),
        "cached_domains": len(recent_recipients),
        "mx_cache_size": get_cached_mx.cache_info().currsize
    })

# =========================
# START WITH PREHEATING
# =========================
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s'
    )
    
    # Preheat connections before starting
    logging.info("🔥 Preheating connections...")
    ultra_pool.preheat()
    logging.info(f"✅ Preheated {len(ultra_pool.connections)} connections")
    
    port = int(os.environ.get("PORT", 5000))
    
    # Run with optimal settings
    app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False)
