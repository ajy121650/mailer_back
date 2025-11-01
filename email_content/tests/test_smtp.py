import pytest
from unittest.mock import patch, MagicMock
from email_content.service.smtp import send_mail_via_smtp, SMTPAuth


@pytest.fixture
def auth():
    return SMTPAuth(username="2019000066@ushs.hs.kr", password="qrez cvzo qvst bnjk", domain_hint="gmail")


@patch("email_content.service.smtp.smtplib.SMTP")  # smtplib.SMTP 객체를 모킹
@patch("email_content.service.smtp.smtplib.SMTP_SSL")  # smtplib.SMTP_SSL 객체도 모킹
def test_send_mail_via_smtp(mock_smtp_ssl, mock_smtp, auth):
    """
    send_mail_via_smtp가 SMTP 서버와의 상호작용을 올바르게 수행하는지 테스트
    """

    # 1️⃣ SMTP 인스턴스를 가짜로 생성
    mock_server = MagicMock()
    mock_smtp.return_value = mock_server
    mock_smtp_ssl.return_value = mock_server

    # 2️⃣ 가짜 응답 구성
    mock_server.send_message.return_value = {}  # 실패 없이 전송 성공

    # 3️⃣ 함수 호출
    result = send_mail_via_smtp(
        auth=auth,
        subject="[테스트] 유닛테스트 메일",
        sender="no-reply@test.com",
        to=["receiver@test.com"],
        text_body="이건 단위테스트입니다.",
    )

    # 4️⃣ 검증
    assert "message_id" in result
    assert result["failed"] == {}
    assert "receiver@test.com" in result["accepted"]

    # 5️⃣ SMTP 호출 검증
    mock_server.login.assert_called_once_with(auth.username, auth.password)
    mock_server.send_message.assert_called_once()
    mock_server.quit.assert_called_once()


def test_real_send_mail(auth):
    text = """
    ପ(๑•ᴗ•๑)ଓ 
    2025-11-01 메일 잘 받으셨나요?
     
    11월 1일 운세 공유 드립니다.

    별자리운세
    1위 전갈자리 
    12위 사수자리
    11위 천칭자리
    10위 쌍둥이자리
    9위 사자자리
    8위 물병자리
    7위 처녀자리
    6위 양자리
    5위 황소자리
    4위 염소자리
    2위 개자리
    3위 물고기자리
    """

    result = send_mail_via_smtp(
        auth=auth,
        subject="[*Mailer*]",
        sender=auth.username,
        to=[
            "ajy1216@snu.ac.kr",
            "dongin1001@snu.ac.kr",
            "korj03kory@snu.ac.kr",
            "bona718@snu.ac.kr",
            "jdnjsyoo@snu.ac.kr",
            "smkl1004@snu.ac.kr",
            "todd4@snu.ac.kr",
            "ggaggu@snu.ac.kr",
            "seraphina0911@snu.ac.kr",
            "seatosky2002@gmail.com",
            "lgmoo2002@snu.ac.kr",
            "0422ll@snu.ac.kr",
            "jych1109@snu.ac.kr",
            "swanchoi1102@snu.ac.kr",
            "chldmstjr0122@gmail.com",
            "paxjc2000@snu.ac.kr",
        ],
        text_body=text,
    )
    print(result)
