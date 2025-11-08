from rest_framework import serializers
from .models import Contact


class ContactSerializer(serializers.ModelSerializer):
    """
    Contact 모델을 위한 Serializer
    - 목록 조회, 생성, 수정에 사용됩니다.
    """

    class Meta:
        model = Contact
        fields = ["id", "address"]
        read_only_fields = ["id"]
