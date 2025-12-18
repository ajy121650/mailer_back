# Create your views here.
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
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
    permission_classes = [IsAuthenticated]

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
        description="특정 템플릿을 인증된 사용자의 여러 이메일 계정으로 복사하여 '내 템플릿'으로 저장합니다. 요청 본문에 `email_account_ids` 리스트를 포함해야 합니다.",
        request={"application/json": {"example": {"email_account_ids": [1, 2]}}},
        responses={201: MyTemplateSerializer(many=True)},
    )
    def post(self, request, pk):
        user = request.user
        email_account_ids = request.data.get("email_account_ids")

        if not isinstance(email_account_ids, list) or not email_account_ids:
            return Response(
                {"error": "email_account_ids must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # 원본 템플릿 조회
            source_template = Template.objects.get(pk=pk)
        except Template.DoesNotExist:
            return Response({"error": "Source template not found"}, status=status.HTTP_404_NOT_FOUND)

        # 요청된 계정들이 모두 사용자의 소유인지 확인
        try:
            cleaned_ids = sorted(list(set(int(i) for i in email_account_ids)))
        except (ValueError, TypeError):
            return Response(
                {"error": "All email_account_ids must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        accounts = list(EmailAccount.objects.filter(user=user, pk__in=cleaned_ids))

        if len(accounts) != len(cleaned_ids):
            return Response(
                {"error": "One or more email accounts were not found or do not belong to you."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 트랜잭션 내에서 템플릿 복사
        created_templates = []
        try:
            with transaction.atomic():
                for account in accounts:
                    new_template = Template.objects.create(
                        user=user,
                        email_account=account,
                        template_content=source_template.template_content,
                        template_title=source_template.template_title,
                        main_category=source_template.main_category,
                        sub_category=source_template.sub_category,
                        topic=source_template.topic,
                    )
                    created_templates.append(new_template)
        except Exception as e:
            return Response(
                {"error": f"An error occurred during template copy: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = MyTemplateSerializer(created_templates, many=True)
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
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="내 템플릿 생성 (다중 계정)",
        description="하나 이상의 이메일 계정에 대한 새 개인 템플릿을 생성합니다. 요청 본문에는 `email_account_ids` 리스트와 템플릿 내용을 담아야 합니다. 템플릿 소유자는 현재 인증된 사용자로 자동 설정됩니다.",
        request={
            "application/json": {
                "example": {
                    "email_account_ids": [1, 2],
                    "template_title": "새로운 템플릿 제목",
                    "template_content": "템플릿 내용입니다.",
                    "sub_category": "업무",
                    "topic": "주간 보고",
                }
            }
        },
        responses={201: MyTemplateSerializer(many=True)},
    )
    def post(self, request):
        user = request.user
        email_account_ids = request.data.get("email_account_ids")

        if not isinstance(email_account_ids, list) or not email_account_ids:
            return Response(
                {"error": "email_account_ids must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MyTemplateCreateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            cleaned_ids = sorted(list(set(int(i) for i in email_account_ids)))
        except (ValueError, TypeError):
            return Response(
                {"error": "All email_account_ids must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        accounts = list(EmailAccount.objects.filter(user=user, pk__in=cleaned_ids))

        if len(accounts) != len(cleaned_ids):
            return Response(
                {"error": "One or more email accounts were not found or do not belong to you."},
                status=status.HTTP_404_NOT_FOUND,
            )

        created_templates = []
        try:
            with transaction.atomic():
                for account in accounts:
                    template = Template.objects.create(
                        user=user,
                        email_account=account,
                        template_content=serializer.validated_data["template_content"],
                        template_title=serializer.validated_data["template_title"],
                        main_category="개인 템플릿",
                        sub_category=serializer.validated_data["sub_category"],
                        topic=serializer.validated_data["topic"],
                    )
                    created_templates.append(template)
        except Exception as e:
            return Response(
                {"error": f"An error occurred during template creation: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_serializer = MyTemplateSerializer(created_templates, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class MyTemplateDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="내 템플릿 상세 조회",
        description="ID로 내가 소유한 특정 템플릿의 상세 내용을 조회합니다.",
        responses=MyTemplateSerializer,
    )
    def get(self, request, pk):
        try:
            template = Template.objects.get(pk=pk, user=request.user)
        except Template.DoesNotExist:
            return Response(
                {"error": "Template not found or you do not have permission to access it"},
                status=status.HTTP_404_NOT_FOUND,
            )

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
            template = Template.objects.get(pk=pk, user=request.user)
        except Template.DoesNotExist:
            return Response(
                {"error": "Template not found or you do not have permission to access it."},
                status=status.HTTP_404_NOT_FOUND,
            )

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
            template = Template.objects.get(pk=pk, user=request.user)
        except Template.DoesNotExist:
            return Response(
                {"error": "Template not found or you do not have permission to access it."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            template.delete()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(status=status.HTTP_204_NO_CONTENT)
