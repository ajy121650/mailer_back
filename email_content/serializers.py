from rest_framework import serializers


class EmailSendSerializer(serializers.Serializer):
    """
    이메일 전송 API의 요청 본문(Request Body) 유효성 검사를 위한 Serializer
    """

    account_id = serializers.IntegerField(help_text="메일을 보낼 EmailAccount의 ID")
    to = serializers.ListField(
        child=serializers.EmailField(),
        allow_empty=False,
        help_text="수신자 이메일 주소 리스트",
    )
    cc = serializers.ListField(
        child=serializers.EmailField(),
        allow_empty=True,
        required=False,
        help_text="참조 이메일 주소 리스트",
    )
    bcc = serializers.ListField(
        child=serializers.EmailField(),
        allow_empty=True,
        required=False,
        help_text="숨은 참조 이메일 주소 리스트",
    )
    subject = serializers.CharField(max_length=255, allow_blank=True, help_text="메일 제목")
    body = serializers.CharField(allow_blank=True, help_text="메일 본문")
    is_html = serializers.BooleanField(default=False, help_text="메일 본문이 HTML 형식인지 여부")
