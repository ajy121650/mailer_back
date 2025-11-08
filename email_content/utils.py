# domain에 따른 IMAP 설정
def get_imap_config(domain: str):
    """
    domain 문자열을 보고 알맞은 IMAP 호스트와 포트 번호를 반환한다.
    """
    domain = domain.lower().strip()

    mapping = {
        "gmail": ("imap.gmail.com", 993),
        "google": ("imap.gmail.com", 993),
        "outlook": ("outlook.office365.com", 993),
        "hotmail": ("outlook.office365.com", 993),
        "live": ("outlook.office365.com", 993),
        "office365": ("outlook.office365.com", 993),
        "naver": ("imap.naver.com", 993),
        "daum": ("imap.daum.net", 993),
        "kakao": ("imap.kakao.com", 993),
        "yahoo": ("imap.mail.yahoo.com", 993),
        "icloud": ("imap.mail.me.com", 993),
        "aol": ("imap.aol.com", 993),
        # 필요시 다른 도메인도 계속 확장 가능
    }

    if domain in mapping:
        return mapping[domain]
    else:
        raise ValueError(f"지원하지 않는 도메인: {domain}")
