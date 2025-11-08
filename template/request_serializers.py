from rest_framework import serializers
from .models import Template


class MyTemplateCreateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ["template_content", "template_title", "sub_category", "topic"]


class MyTemplateUpdateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ["sub_category", "topic", "template_title", "template_content"]
