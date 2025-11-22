# Create your views here.
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import Template
from user.models import User
from .serializers import MyTemplateSerializer, ViewTemplateSerializer
from .request_serializers import MyTemplateCreateRequestSerializer, MyTemplateUpdateRequestSerializer
from email_account.models import EmailAccount


class ViewTemplateListView(APIView):
    @extend_schema(
        summary="관리자 제공 템플릿 목록 조회",
        description="관리자(user_id='common_template_admin')가 생성한 모든 템플릿의 목록을 조회합니다.",
        responses=ViewTemplateSerializer(many=True),
        operation_id="view_template_list",
    )
    def get(self, request):
        try:
            admin = User.objects.filter(user_id="common_template_admin").first()
        except User.DoesNotExist:
            return Response({"error": "Admin user not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            templates = Template.objects.filter(user=admin)
        except Template.DoesNotExist:
            return Response({"error": "No templates found for admin user"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ViewTemplateSerializer(templates, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ViewTemplateDetailView(APIView):
    @extend_schema(
        summary="특정 템플릿 상세 조회",
        description="ID로 특정 템플릿의 상세 내용을 조회합니다.",
        responses=ViewTemplateSerializer,
        operation_id="view_template_retrieve",
    )
    def get(self, request, pk):
        try:
            template = Template.objects.get(pk=pk)
        except Template.DoesNotExist:
            return Response({"error": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ViewTemplateSerializer(template)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="내 템플릿으로 가져오기",
        description="특정 템플릿을 지정된 사용자의 이메일 계정들로 복사하여 '내 템플릿'으로 저장합니다.",
        request={"application/json": {"example": {"user_id": 1, "email_account_ids": [1, 2]}}},
        responses={201: MyTemplateSerializer(many=True)},
    )
    def post(self, request, pk):
        # Expect JSON body: { "user_id": int, "email_account_ids": [int, ...] }
        data = request.data if isinstance(request.data, dict) else {}

        user_id = data.get("user_id")
        email_account_ids = data.get("email_account_ids")

        # Basic presence and type checks
        if user_id is None:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(email_account_ids, list):
            return Response({"error": "email_account_ids must be a list"}, status=status.HTTP_400_BAD_REQUEST)

        # Normalize and validate ids are integers
        try:
            cleaned_account_ids = [int(x) for x in email_account_ids]
        except (ValueError, TypeError):
            return Response({"error": "email_account_ids must contain integers"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate user exists
        try:
            user = User.objects.get(id=int(user_id))
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Optionally validate template exists (since pk is in URL)
        try:
            template = Template.objects.get(pk=pk)
        except Template.DoesNotExist:
            return Response({"error": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

        # Optionally check provided email accounts exist
        existing_accounts = EmailAccount.objects.filter(id__in=cleaned_account_ids)

        templates = []
        for account in existing_accounts:
            template = Template.objects.create(
                user=user,
                email_account=account,
                template_content=template.template_content,
                template_title=template.template_title,
                main_category=template.main_category,
                sub_category=template.sub_category,
                topic=template.topic,
            )
            templates.append(template)

        serializer = MyTemplateSerializer(templates, many=True)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="템플릿 삭제 (관리자용)", description="특정 템플릿을 영구적으로 삭제합니다.", responses={204: None}
    )
    def delete(self, request, pk):
        try:
            template = Template.objects.get(pk=pk)
        except Template.DoesNotExist:
            return Response({"error": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            template.delete()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(status=status.HTTP_204_NO_CONTENT)


class MyTemplateListView(APIView):
    @extend_schema(
        summary="내 템플릿 목록 조회",
        description="특정 사용자가 소유한 모든 템플릿 목록을 조회합니다.",
        responses=MyTemplateSerializer(many=True),
    )
    def get(self, request, pk):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            templates = Template.objects.select_related("email_account").filter(user=user)
        except Template.DoesNotExist:
            return Response({"error": "No templates found for user"}, status=status.HTTP_404_NOT_FOUND)

        serializer = MyTemplateSerializer(templates, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MyTemplateCreateView(APIView):
    @extend_schema(
        summary="내 템플릿 생성",
        description="새로운 개인 템플릿을 생성합니다.",
        request=MyTemplateCreateRequestSerializer,
        responses={201: MyTemplateSerializer},
    )
    def post(self, request):
        user_id = request.query_params.get("user_id")
        email_account_id = request.query_params.get("email_account_id")

        serializer = MyTemplateCreateRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(id=user_id).first()
        email_account = EmailAccount.objects.filter(id=email_account_id).first()

        if user is None:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        if email_account is None:
            return Response({"error": "Email account not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Create the template
            template = Template.objects.create(
                user=user,
                email_account=email_account,
                template_content=serializer.validated_data["template_content"],
                template_title=serializer.validated_data["template_title"],
                main_category="개인 템플릿",
                sub_category=serializer.validated_data["sub_category"],
                topic=serializer.validated_data["topic"],
            )

            serializer = MyTemplateSerializer(template)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MyTemplateDetailView(APIView):
    @extend_schema(
        summary="내 템플릿 상세 조회",
        description="ID로 내가 소유한 특정 템플릿의 상세 내용을 조회합니다.",
        responses=MyTemplateSerializer,
    )
    def get(self, request, pk):
        try:
            template = Template.objects.get(pk=pk)
        except Template.DoesNotExist:
            return Response({"error": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = MyTemplateSerializer(template)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="내 템플릿 수정",
        description="ID로 내가 소유한 특정 템플릿의 내용을 수정합니다.",
        request=MyTemplateUpdateRequestSerializer,
        responses={200: None},
    )
    def put(self, request, pk):
        try:
            template = Template.objects.get(pk=pk)
        except Template.DoesNotExist:
            return Response({"error": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = MyTemplateUpdateRequestSerializer(data=request.data, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            template.sub_category = serializer.validated_data["sub_category"]
            template.topic = serializer.validated_data["topic"]
            template.template_title = serializer.validated_data["template_title"]
            template.template_content = serializer.validated_data["template_content"]
            template.save()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(status=status.HTTP_200_OK)

    @extend_schema(
        summary="내 템플릿 삭제",
        description="ID로 내가 소유한 특정 템플릿을 삭제합니다.",
        responses={204: None},
    )
    def delete(self, request, pk):
        try:
            template = Template.objects.get(pk=pk)
        except Template.DoesNotExist:
            return Response({"error": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            template.delete()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(status=status.HTTP_204_NO_CONTENT)
