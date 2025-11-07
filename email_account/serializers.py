from rest_framework import serializers
from .models import EmailAccount


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
        fields = ["address", "password", "domain"]

    def create(self, validated_data):
        user = self.context["request"].user
        password = validated_data.pop("password")

        # 주소와 사용자로 이미 계정이 있는지 확인
        if EmailAccount.objects.filter(user=user, address=validated_data.get("address")).exists():
            raise serializers.ValidationError({"detail": "This email account is already registered."})

        # 모델의 email_password.setter를 사용하여 암호화
        instance = EmailAccount(user=user, **validated_data)
        instance.email_password = password
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
