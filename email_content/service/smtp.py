import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid, formatdate
from ..utils import get_smtp_config


class SMTPAuth:
    def __init__(self, username: str, password: str, domain_hint: str = None):
        self.username = username
        self.password = password
        self.domain_hint = domain_hint


def _build_message(
    subject: str,
    sender: str,
    to: list[str],
    cc: list[str] | None,
    bcc: list[str] | None,
    text_body: str | None,
    html_body: str | None,
    reply_to: str | None,
    headers: dict | None,
    attachments: list[dict] | None,  # [{"filename": "...", "content": bytes, "mime": "application/pdf"}]
):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if reply_to:
        msg["Reply-To"] = reply_to
    # Date/Message-ID
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=sender.split("@")[-1])

    # 커스텀 헤더
    for k, v in (headers or {}).items():
        if k.lower() not in {"from", "to", "cc", "bcc", "subject", "date", "message-id"}:
            msg[k] = str(v)

    # 본문
    if html_body and text_body:
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")
    elif html_body:
        msg.add_alternative(html_body, subtype="html")
    else:
        msg.set_content(text_body or "")

    # 첨부
    for att in attachments or []:
        # MIME 타입 분리 (mime 키로 찾아오는데, 없으면 application/octet-stream)
        maintype, _, subtype = (att.get("mime", "application/octet-stream")).partition("/")
        msg.add_attachment(att["content"], maintype=maintype, subtype=subtype, filename=att.get("filename", "file"))

    return msg


def _connect(auth: SMTPAuth):
    cfg = get_smtp_config(auth.domain_hint or auth.username.split("@")[-1].split(".")[0])
    host, port = cfg["host"], cfg["port"]
    use_ssl = cfg.get("ssl", False)
    use_starttls = cfg.get("starttls", False)

    if use_ssl:
        server = smtplib.SMTP_SSL(host, port, timeout=20, context=ssl.create_default_context())
    else:
        server = smtplib.SMTP(host, port, timeout=20)
        server.ehlo()
        if use_starttls:
            server.starttls(context=ssl.create_default_context())
            server.ehlo()

    server.login(auth.username, auth.password)
    return server


def send_mail_via_smtp(
    auth: SMTPAuth,
    subject: str,
    sender: str,
    to: list[str],
    text_body: str | None = None,
    html_body: str | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    reply_to: str | None = None,
    headers: dict | None = None,
    attachments: list[dict] | None = None,
    envelope_from: str | None = None,  # bounce 주소(Return-Path), 반송될때 돌아갈 주소
):
    msg = _build_message(subject, sender, to, cc, bcc, text_body, html_body, reply_to, headers, attachments)

    # 수신 전체 목록 (중복 제거 로직 포함)
    all_rcpts = list(dict.fromkeys((to or []) + (cc or []) + (bcc or [])))

    # Return-Path(Envelope-From)
    mail_from = envelope_from or sender

    # 연결/송신
    server = _connect(auth)
    try:
        resp = server.send_message(msg, from_addr=mail_from, to_addrs=all_rcpts)
        # resp: 실패한 주소 딕셔너리(비어있으면 전부 성공)
        return {"message_id": msg["Message-ID"], "failed": resp, "accepted": [r for r in all_rcpts if r not in resp]}
    finally:
        try:
            server.quit()
        except Exception:
            pass
