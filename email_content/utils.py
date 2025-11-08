# domain에 따른 IMAP 설정
def get_imap_config(domain: str):
    """
    domain 문자열을 보고 알맞은 IMAP 호스트, 포트, 보안 설정을 반환한다.
    """
    domain = domain.lower().strip()

    table = {
        "gmail": {"host": "imap.gmail.com", "port": 993, "ssl": True},
        "google": {"host": "imap.gmail.com", "port": 993, "ssl": True},
        "outlook": {"host": "outlook.office365.com", "port": 993, "ssl": True},
        "hotmail": {"host": "outlook.office365.com", "port": 993, "ssl": True},
        "live": {"host": "outlook.office365.com", "port": 993, "ssl": True},
        "office365": {"host": "outlook.office365.com", "port": 993, "ssl": True},
        "naver": {"host": "imap.naver.com", "port": 993, "ssl": True},
        "daum": {"host": "imap.daum.net", "port": 993, "ssl": True},
        "kakao": {"host": "imap.kakao.com", "port": 993, "ssl": True},
        "yahoo": {"host": "imap.mail.yahoo.com", "port": 993, "ssl": True},
        "icloud": {"host": "imap.mail.me.com", "port": 993, "ssl": True},
        "aol": {"host": "imap.aol.com", "port": 993, "ssl": True},
    }

    if domain in table:
        return table[domain]
    else:
        raise ValueError(f"지원하지 않는 도메인: {domain}")


def get_smtp_config(domain: str):
    """
    domain 문자열을 보고 알맞은 SMTP 호스트, 포트, 보안 설정을 반환한다.
    """
    domain = (domain or "").lower().strip()

    table = {
        "gmail": {"host": "smtp.gmail.com", "port": 587, "starttls": True},
        "google": {"host": "smtp.gmail.com", "port": 587, "starttls": True},
        "naver": {"host": "smtp.naver.com", "port": 587, "starttls": True},
        "daum": {"host": "smtp.daum.net", "port": 465, "ssl": True},
        "kakao": {"host": "smtp.kakao.com", "port": 465, "ssl": True},
        "outlook": {"host": "smtp-mail.outlook.com", "port": 587, "starttls": True},
        "office365": {"host": "smtp.office365.com", "port": 587, "starttls": True},
        "yahoo": {"host": "smtp.mail.yahoo.com", "port": 465, "ssl": True},
        "icloud": {"host": "smtp.mail.me.com", "port": 587, "starttls": True},
    }

    if domain in table:
        return table[domain]
    else:
        raise ValueError(f"지원하지 않는 도메인: {domain}")

    # return table.get(domain, {"host": f"smtp.{domain}.com", "port": 587, "starttls": True})
