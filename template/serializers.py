from rest_framework import serializers
from .models import Template


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ["id", "user", "email_account", "template_content", "main_category", "sub_category", "topic"]
