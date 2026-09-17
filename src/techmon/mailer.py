"""로컬 테스트용 Gmail SMTP 발송 (CI는 워크플로우의 action-send-mail 사용)."""
import os
import smtplib
from email.mime.text import MIMEText


def send(subject, html):
    user = os.environ.get("MAIL_USERNAME", "")
    password = os.environ.get("MAIL_APP_PASSWORD", "")
    to = os.environ.get("MAIL_TO") or user
    if not (user and password):
        print("[!] MAIL_USERNAME / MAIL_APP_PASSWORD 미설정 — 발송 생략")
        return False
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = subject, f"Tech Monitoring <{user}>", to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(user, password)
        s.sendmail(user, [x.strip() for x in to.split(",") if x.strip()], msg.as_string())
    print(f"메일 발송: {to}")
    return True
