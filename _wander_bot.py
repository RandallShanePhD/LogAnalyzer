#!/usr/bin/python3
import imaplib
import smtplib
import email
import os
import sys
import time
import io
import datetime
from contextlib import redirect_stdout
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "Bot"))
from decode import load_igc
from kmls import create_enhanced_kml
from display import display_summary_stats

IMAP_SERVER = os.getenv("IMAP_SERVER", "mail.privateemail.com")
IMAP_USER = os.getenv("IMAP_USER", "wanderbot@wanderexpeditions.com")
IMAP_PASS = os.getenv("IMAP_PASS", "gufpin-syfdi5-pIzpir")
SMTP_SERVER = os.getenv("SMTP_SERVER", IMAP_SERVER)
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
ERROR_NOTIFY = os.getenv("ERROR_NOTIFY", "randall@wanderexpeditions.com")
LOG_DIR = Path(__file__).parent / "Log"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LAST_REPORT_FILE = LOG_DIR / ".last_weekly_report"


def send_error_notification(sender, filename, error):
    msg = MIMEText(
        f"Error processing IGC file from {sender}\n\n"
        f"File: {filename}\n"
        f"Error: {error}\n\n"
        f"Time: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}"
    )
    msg["From"] = IMAP_USER
    msg["To"] = ERROR_NOTIFY
    msg["Subject"] = f"Wander Bot Error — {filename}"
    try:
        send_reply(msg)
    except Exception as e:
        print(f"Failed to send error notification: {e}")


def log_processing(sender, filename):
    entry = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {sender} | {filename}\n"
    with open(LOG_DIR / "wanderbot.log", "a") as f:
        f.write(entry)


def connect():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(IMAP_USER, IMAP_PASS)
    mail.select("INBOX")
    return mail


def build_reply(sender, filename, body, kml_path):
    reply = MIMEMultipart("mixed")
    reply["From"] = IMAP_USER
    reply["To"] = sender
    reply["Subject"] = f"Analysis of your flight: {filename}"
    reply.attach(MIMEText(body, "plain"))

    if kml_path and os.path.exists(kml_path):
        with open(kml_path, "rb") as f:
            attachment = MIMEBase("application", "vnd.google-earth.kml+xml")
            attachment.set_payload(f.read())
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=os.path.basename(kml_path),
        )
        reply.attach(attachment)

    return reply


def send_reply(reply_email):
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(IMAP_USER, IMAP_PASS)
        smtp.send_message(reply_email)


def process_igc(part, envelope, igc_path, note=""):
    filename = part.get_filename()
    sender = envelope.get("From", "")

    results = load_igc(igc_path)

    buf = io.StringIO()
    with redirect_stdout(buf):
        display_summary_stats(results)
    body = buf.getvalue()

    display_summary_stats(results)

    if note:
        body += f"\n{note}\n"

    kml_path = igc_path.rsplit(".", 1)[0] + ".kml"
    create_enhanced_kml(results["kml_data"])

    if os.path.exists(kml_path):
        reply = build_reply(sender, filename, body, kml_path)
        send_reply(reply)

    log_processing(sender, filename)


def fetch_igc_attachments(mail):
    result, data = mail.search(None, "UNSEEN")
    if result != "OK":
        return

    for num in data[0].split():
        result, msg_data = mail.fetch(num, "(RFC822)")
        if result != "OK":
            continue

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        igc_parts = []
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get("Content-Disposition") is None:
                continue
            filename = part.get_filename()
            if filename and filename.lower().endswith(".igc"):
                igc_parts.append(part)

        if not igc_parts:
            continue

        part = igc_parts[0]
        filename = part.get_filename()
        note = "Only 1 file per email is processed; additional IGC files were ignored." if len(igc_parts) > 1 else ""

        igc_path = str(LOG_DIR / filename)
        payload = part.get_payload(decode=True)
        if isinstance(payload, str):
            payload = payload.encode()
        with open(igc_path, "wb") as f:
            f.write(bytes(payload))

        try:
            print(f"Processing: {filename} from {msg['From']}")
            process_igc(part, msg, igc_path, note)
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            send_error_notification(msg["From"], filename, e)

        mail.store(num, "+FLAGS", "\\Seen")


def send_weekly_summary():
    log_path = LOG_DIR / "wanderbot.log"
    if not log_path.exists():
        return

    senders = set()
    count = 0
    with open(log_path) as f:
        for line in f:
            parts = line.strip().split(" | ")
            if len(parts) >= 2:
                senders.add(parts[1])
                count += 1

    msg = MIMEText(
        f"Wander Bot Weekly Summary\n\n"
        f"Files analyzed: {count}\n"
        f"Unique senders: {len(senders)}\n"
        f"Period: All time (log resets on send)\n\n"
        f"Report generated: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}"
    )
    msg["From"] = IMAP_USER
    msg["To"] = ERROR_NOTIFY
    msg["Subject"] = "Wander Bot Weekly Summary"
    send_reply(msg)

    log_path.unlink()


def poll_forever():
    print(f"Monitoring {IMAP_USER} every {POLL_INTERVAL}s ...")
    while True:
        try:
            mail = connect()
            fetch_igc_attachments(mail)
            mail.logout()
        except Exception as e:
            print(f"Connection error: {e}")

        today = datetime.date.today()
        if today.weekday() == 5:
            last_report = None
            if LAST_REPORT_FILE.exists():
                last_report = LAST_REPORT_FILE.read_text().strip()
            if last_report != str(today):
                print("Sending weekly summary ...")
                try:
                    send_weekly_summary()
                    LAST_REPORT_FILE.write_text(str(today))
                except Exception as e:
                    print(f"Weekly summary error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    poll_forever()

