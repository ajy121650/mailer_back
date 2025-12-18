import os
import django
import json
import sys


# --------------------------------------------------
# Django 환경 설정
# --------------------------------------------------
def setup_django():
    """
    Standalone 스크립트에서 Django 환경을 설정합니다.
    프로젝트 루트를 sys.path에 추가해야 모델을 임포트할 수 있습니다.
    """
    # 이 스크립트 파일(test_setup/inject_common_templates.py)의 상위 디렉터리(test_setup)의
    # 상위 디렉터리(프로젝트 루트)를 경로에 추가
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_root)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        django.setup()
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc


# --------------------------------------------------
#  메인 로직
# --------------------------------------------------
def main():
    """
    공용 템플릿을 데이터베이스에 주입하는 메인 함수
    """
    print("Django 환경을 설정합니다...")
    setup_django()

    from user.models import User
    from template.models import Template

    print("공용 템플릿 관리자 계정을 확인/생성합니다...")
    admin_user, created = User.objects.get_or_create(user_id="common_template_admin")
    if created:
        print(f"'{admin_user.user_id}' 관리자 계정을 새로 생성했습니다.")
    else:
        print(f"'{admin_user.user_id}' 관리자 계정이 이미 존재합니다.")

    # 스크립트와 동일한 디렉터리에 있는 TEMPLATE.json 파일 경로 설정
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_file_path = os.path.join(script_dir, "TEMPLATE.json")

    print(f"{template_file_path} 파일을 읽고 있습니다...")
    try:
        with open(template_file_path, "r", encoding="utf-8") as f:
            templates_data = json.load(f)
    except FileNotFoundError:
        print(f"에러: {template_file_path}에서 TEMPLATE.json 파일을 찾을 수 없습니다.")
        return
    except json.JSONDecodeError:
        print(f"에러: {template_file_path} 파일이 유효한 JSON 형식이 아닙니다.")
        return

    added_count = 0
    skipped_count = 0

    print("데이터베이스에 템플릿 주입을 시작합니다...")
    for tpl in templates_data:
        title = tpl.get("title")
        if not title:
            print(f"경고: 'title'이 없는 템플릿 데이터(ID: {tpl.get('id')})를 건너뜁니다.")
            skipped_count += 1
            continue

        if Template.objects.filter(user=admin_user, template_title=title).exists():
            skipped_count += 1
        else:
            Template.objects.create(
                user=admin_user,
                template_title=title,
                template_content=tpl.get("body", ""),
                main_category=tpl.get("mainCategory", ""),
                sub_category=tpl.get("subCategory", ""),
                topic=tpl.get("topic", ""),
            )
            added_count += 1
            print(f"'{title}' 템플릿을 추가했습니다.")

    print("\n----- 작업 완료 -----")
    print(f"새로 추가된 템플릿: {added_count}개")
    print(f"이미 존재하여 건너뛴 템플릿: {skipped_count}개")
    print(f"총 처리한 템플릿: {len(templates_data)}개")


if __name__ == "__main__":
    main()
