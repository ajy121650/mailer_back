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
    html_text = """
    <!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width">
  <title>11월 1일 운세</title>
  <!-- 일부 클라이언트의 다크모드/폰트 대응 -->
  <meta name="color-scheme" content="light only">
  <meta name="supported-color-schemes" content="light">
  <style>
    /* 모바일에서 텍스트 크기 자동 확대 방지 (iOS) */
    body, table, td, a { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
    /* Outlook용 이미지 간격 버그 방지 */
    img { -ms-interpolation-mode: bicubic; }
  </style>
</head>
<body style="margin:0; padding:0; background-color:#f5f7fb;">
  <!-- 프리헤더(미리보기 문구) -->
  <div style="display:none; max-height:0; overflow:hidden; opacity:0; color:transparent;">
    2025-11-01 메일 잘 받으셨나요? 11월 1일 별자리 운세를 확인해보세요.
  </div>

  <!-- 전체 래퍼 -->
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
    <tr>
      <td align="center" style="padding:24px;">
        <!-- 카드 -->
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:600px; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 2px 10px rgba(0,0,0,0.04);">
          <!-- 헤더 -->
          <tr>
            <td style="padding:28px 28px 16px 28px; background:linear-gradient(135deg,#eef3ff,#ffffff);">
              <div style="font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#1f2937; font-size:20px; line-height:1.5;">
                <span style="font-size:24px;">ପ(๑•ᴗ•๑)ଓ</span><br>
                <strong>2025-11-01 메일 잘 받으셨나요?</strong>
              </div>
            </td>
          </tr>

          <!-- 본문 인사 -->
          <tr>
            <td style="padding:0 28px 8px 28px;">
              <p style="margin:0; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#374151; font-size:15px; line-height:1.7;">
                11월 1일 운세 공유 드립니다.
              </p>
            </td>
          </tr>

          <!-- 섹션 타이틀 -->
          <tr>
            <td style="padding:8px 28px 0 28px;">
              <h2 style="margin:0; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#111827; font-size:18px; line-height:1.5;">
                ⭐ 별자리운세
              </h2>
            </td>
          </tr>

          <!-- 순위 리스트 (표 형식: 이메일 호환성 우수) -->
          <tr>
            <td style="padding:12px 20px 24px 20px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border-collapse:separate; border-spacing:0 8px;">
                <!-- 1위 -->
                <tr>
                  <td style="width:72px; background:#f1f5ff; border-radius:8px; text-align:center; padding:10px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#1d4ed8; font-weight:700; font-size:14px;">1위</td>
                  <td style="background:#f9fbff; border-radius:8px; padding:10px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#1f2937; font-size:14px;">전갈자리</td>
                </tr>
                <!-- 12위 -->
                <tr>
                  <td style="width:72px; background:#fff7f7; border-radius:8px; text-align:center; padding:10px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#b91c1c; font-weight:700; font-size:14px;">12위</td>
                  <td style="background:#fffafa; border-radius:8px; padding:10px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#1f2937; font-size:14px;">사수자리</td>
                </tr>
                <!-- 11위 -->
                <tr>
                  <td style="width:72px; background:#f8fafc; border-radius:8px; text-align:center; padding:10px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#6b7280; font-weight:700; font-size:14px;">11위</td>
                  <td style="background:#fbfdff; border-radius:8px; padding:10px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#1f2937; font-size:14px;">천칭자리</td>
                </tr>
                <!-- 10위 -->
                <tr>
                  <td style="width:72px; background:#f8fafc; border-radius:8px; text-align:center; padding:10px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#6b7280; font-weight:700; font-size:14px;">10위</td>
                  <td style="background:#fbfdff; border-radius:8px; padding:10px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#1f2937; font-size:14px;">쌍둥이자리</td>
                </tr>
                <!-- 9위 -->
                <tr>
                  <td style="width:72px; background:#f8fafc; border-radius:8px; text-align:center; padding:10px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#6b7280; font-weight:700; font-size:14px;">9위</td>
                  <td style="background:#fbfdff; border-radius:8px; padding:10px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#1f2937; font-size:14px;">사자자리</td>
                </tr>
                <!-- 8위 -->
                <tr>
                  <td style="width:72px; background:#f8fafc; border-radius:8px; text-align:center; padding:10px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#6b7280; font-weight:700; font-size:14px;">8위</td>
                  <td style="background:#fbfdff; border-radius:8px; padding:10px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#1f2937; font-size:14px;">물병자리</td>
                </tr>
                <!-- 7위 -->
                <tr>
                  <td style="width:72px; background:#f8fafc; border-radius:8px; text-align:center; padding:10px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#6b7280; font-weight:700; font-size:14px;">7위</td>
                  <td style="background:#fbfdff; border-radius:8px; padding:10px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#1f2937; font-size:14px;">처녀자리</td>
                </tr>
                <!-- 6위 -->
                <tr>
                  <td style="width:72px; background:#f8fafc; border-radius:8px; text-align:center; padding:10px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#6b7280; font-weight:700; font-size:14px;">6위</td>
                  <td style="background:#fbfdff; border-radius:8px; padding:10px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#1f2937; font-size:14px;">양자리</td>
                </tr>
                <!-- 5위 -->
                <tr>
                  <td style="width:72px; background:#eefbf3; border-radius:8px; text-align:center; padding:10px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#047857; font-weight:700; font-size:14px;">5위</td>
                  <td style="background:#f5fdf8; border-radius:8px; padding:10px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#1f2937; font-size:14px;">황소자리</td>
                </tr>
                <!-- 4위 -->
                <tr>
                  <td style="width:72px; background:#eefbf3; border-radius:8px; text-align:center; padding:10px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#047857; font-weight:700; font-size:14px;">4위</td>
                  <td style="background:#f5fdf8; border-radius:8px; padding:10px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#1f2937; font-size:14px;">염소자리</td>
                </tr>
                <!-- 2위 -->
                <tr>
                  <td style="width:72px; background:#e7f5ff; border-radius:8px; text-align:center; padding:10px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#0ea5e9; font-weight:800; font-size:14px;">2위</td>
                  <td style="background:#f3faff; border-radius:8px; padding:10px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#1f2937; font-size:14px;">게자리</td>
                </tr>
                <!-- 3위 -->
                <tr>
                  <td style="width:72px; background:#e7f5ff; border-radius:8px; text-align:center; padding:10px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#0ea5e9; font-weight:800; font-size:14px;">3위</td>
                  <td style="background:#f3faff; border-radius:8px; padding:10px 14px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#1f2937; font-size:14px;">물고기자리</td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- 푸터 -->
          <tr>
            <td style="padding:18px 28px 28px 28px; border-top:1px solid #eef2f7;">
              <p style="margin:0; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Segoe UI', Roboto, NotoSansKR, Arial, sans-serif; color:#6b7280; font-size:12px; line-height:1.6;">
                본 메일은 보기 전용 HTML 예시입니다. 답장은 이 주소로 회신해주세요.
              </p>
            </td>
          </tr>
        </table>
        <!-- 카드 끝 -->
      </td>
    </tr>
  </table>
</body>
</html>
    """

    result = send_mail_via_smtp(
        auth=auth,
        subject="[*Mailer*]",
        sender=auth.username,
        to=[
            "rhj080471i@snu.ac.kr",
            "hoyaho03@snu.ac.kr",
            "paull07@snu.ac.kr",
            "almighty5@snu.ac.kr",
            "eunjae1004@snu.ac.kr",
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
        html_body=html_text,
    )
    print(result)
