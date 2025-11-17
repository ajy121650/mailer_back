from rest_framework import serializers
from .models import EmailAccount
from email_content.utils import get_imap_config
import imaplib


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

    def validate(self, data):
        address = data.get("address")
        password = data.get("password")

        if not address or not password:
            raise serializers.ValidationError("이메일과 앱 비밀번호는 필수 항목입니다.")

        try:
            # 1. 이메일 주소에서 도메인 추출
            full_domain = address.split("@")[1]
            simple_domain = full_domain.split(".")[0].lower()

            # 2. 도메인으로 IMAP 호스트 주소 가져오기
            imap_config = get_imap_config(simple_domain)
            imap_host = imap_config["host"]
            imap_port = imap_config["port"]

            # 3. IMAP 서버 연결 및 로그인 테스트
            with imaplib.IMAP4_SSL(imap_host, imap_port) as imap:
                imap.login(address, password)
                # 로그인 성공 시 바로 로그아웃
                imap.logout()

            # 검증 성공 시, create 메소드에서 사용할 수 있도록 imap_host를 data에 추가
            data["imap_host"] = imap_host
            return data

        except (IndexError, AttributeError):
            raise serializers.ValidationError({"address": "유효하지 않은 이메일 주소 형식입니다."})
        except ValueError:  # get_imap_config에서 지원하지 않는 도메인일 경우
            raise serializers.ValidationError({"address": "현재 지원하지 않는 도메인입니다."})
        except imaplib.IMAP4.error:
            raise serializers.ValidationError("잘못된 이메일 주소 또는 앱 비밀번호입니다. IMAP 접속에 실패했습니다.")
        except Exception as e:
            raise serializers.ValidationError(f"알 수 없는 오류가 발생했습니다: {str(e)}")

    def create(self, validated_data):
        user = self.context["request"].user
        address = validated_data.get("address")
        password = validated_data.pop("password")
        imap_host = validated_data.get("imap_host")  # validate에서 추가된 호스트 정보

        if EmailAccount.objects.filter(user=user, address=address).exists():
            raise serializers.ValidationError({"detail": "This email account is already registered."})

        # validate에서 이미 검증되었으므로 바로 인스턴스 생성
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
