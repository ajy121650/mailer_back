from django.db import models

class Contact(models.Model):
    # 이 주소록을 소유한 이메일 계정
    account = models.ForeignKey('user.EmailAccount', on_delete=models.CASCADE, related_name='contacts', verbose_name="소유 계정")
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="이름")
    email_address = models.EmailField(verbose_name="이메일 주소")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")

    class Meta:
        verbose_name = "주소록"
        verbose_name_plural = "주소록 목록"
        # 한 계정 내에서는 동일한 이메일 주소가 중복되지 않도록 설정
        unique_together = ('account', 'email_address')

    def __str__(self):
        return self.name or self.email_address