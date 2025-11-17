from rest_framework import serializers
from .models import EmailAccount
from email_content.utils import get_imap_config


class EmailAccountSerializer(serializers.ModelSerializer):
    """
    EmailAccount 모델의 목록 조회를 위한 Serializer
    """

    class Meta:
        model = EmailAccount
        fields = [
            "id",
            "address",
            "domain",
            "is_valid",
            "last_synced",
            "job",
            "usage",
            "interests",
        ]


class EmailAccountCreateSerializer(serializers.ModelSerializer):
    """
    EmailAccount 생성을 위한 Serializer
    """

    password = serializers.CharField(write_only=True)

    class Meta:
        model = EmailAccount
        fields = ["address", "password"]

    def create(self, validated_data):
        user = self.context["request"].user
        address = validated_data.get("address")
        password = validated_data.pop("password")

        if EmailAccount.objects.filter(user=user, address=address).exists():
            raise serializers.ValidationError({"detail": "This email account is already registered."})

        try:
            # 1. 이메일 주소에서 도메인 추출 (예: 'user@gmail.com' -> 'gmail')
            full_domain = address.split("@")[1]
            simple_domain = full_domain.split(".")[0].lower()

            # 2. 도메인으로 IMAP 호스트 주소 가져오기
            imap_config = get_imap_config(simple_domain)
            imap_host = imap_config["host"]

        except (IndexError, AttributeError):
            raise serializers.ValidationError({"address": "유효하지 않은 이메일 주소 형식입니다."})
        except ValueError as e:  # get_imap_config에서 지원하지 않는 도메인일 경우
            raise serializers.ValidationError({"address": str(e)})

        # 3. 추출된 도메인으로 EmailAccount 인스턴스 생성
        instance = EmailAccount(user=user, address=address, domain=imap_host)
        instance.email_password = password  # setter를 통해 비밀번호 암호화
        instance.save()
        return instance


class EmailAccountProfileSerializer(serializers.ModelSerializer):
    """
    EmailAccount 프로필 수정을 위한 Serializer
    """

    class Meta:
        model = EmailAccount
        fields = ["job", "usage", "interests"]
        extra_kwargs = {"interests": {"error_messages": {"invalid": "This field must be a list."}}}
