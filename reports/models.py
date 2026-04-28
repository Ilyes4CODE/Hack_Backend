from django.db import models
from django.conf import settings


class WeeklyReport(models.Model):

    STATUS = [
        ('generating', 'Generating'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
    ]

    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports')
    week_start = models.DateField()
    week_end = models.DateField()
    pdf_file = models.FileField(upload_to='reports/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='generating')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report {self.week_start} → {self.week_end} by {self.generated_by}"