# Create your views here.
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Template
from .serializers import TemplateSerializer


class TemplateListView(APIView):
    def get(self, request):
        templates = Template.objects.all()
        serializer = TemplateSerializer(templates, many=True)
        return Response(serializer.data)


class TemplateDetailView(APIView):
    def get(self, request, pk):
        try:
            template = Template.objects.get(pk=pk)
        except Template.DoesNotExist:
            return Response({"error": "Template not found"}, status=404)

        serializer = TemplateSerializer(template)
        return Response(serializer.data)

    def delete(self, request, pk):
        try:
            template = Template.objects.get(pk=pk)
        except Template.DoesNotExist:
            return Response({"error": "Template not found"}, status=404)

        try:
            template.delete()
        except Exception as e:
            return Response({"error": str(e)}, status=500)

        return Response(status=204)
