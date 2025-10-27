from rest_framework import serializers
from .models import Template


class TemplateUpdateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ["email_account", "template_content", "main_category", "sub_category", "topic"]
