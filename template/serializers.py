from rest_framework import serializers
from .models import Template
from email_account.models import EmailAccount


class EmailAccountInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailAccount
        fields = ["id", "address"]


class MyTemplateSerializer(serializers.ModelSerializer):
    """Template model serializer"""

    email_account = EmailAccountInfoSerializer()

    class Meta:
        model = Template
        fields = [
            "id",
            "main_category",
            "sub_category",
            "topic",
            "template_title",
            "template_content",
            "email_account",
            "created_at",
        ]


class ViewTemplateSerializer(serializers.ModelSerializer):
    """Template model serializer for viewing templates"""

    class Meta:
        model = Template
        fields = ["id", "main_category", "sub_category", "topic", "template_title", "template_content", "created_at"]
