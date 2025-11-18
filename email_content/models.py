from django.db import models


class EmailContent(models.Model):
    message_id = models.CharField(max_length=255, null=True, blank=True)
    gm_msgid = models.CharField(max_length=255, null=True, blank=True)
    subject = models.CharField(max_length=255, null=True, blank=True)
    from_header = models.TextField(null=True, blank=True)
    to_header = models.JSONField(null=True, blank=True)
    cc_header = models.JSONField(null=True, blank=True)
    bcc_header = models.JSONField(null=True, blank=True)
    text_body = models.TextField(null=True, blank=True)
    html_body = models.TextField(null=True, blank=True)
    has_attachment = models.BooleanField(default=False)
    date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.subject or "(No Subject)"
