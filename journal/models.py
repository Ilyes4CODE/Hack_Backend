from django.db import models
from django.conf import settings


class FieldLog(models.Model):

    ACTION_TYPES = [
        ('watering', 'Watering'),
        ('treatment', 'Treatment'),
        ('planting', 'Planting'),
        ('harvesting', 'Harvesting'),
        ('fertilizing', 'Fertilizing'),
        ('observation', 'Observation'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='field_logs')
    crop = models.CharField(max_length=100)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} — {self.action_type} — {self.crop} — {self.date}"


class WeatherAlert(models.Model):

    ALERT_TYPES = [
        ('rain', 'Rain Warning'),
        ('heat', 'Heat Warning'),
        ('frost', 'Frost Warning'),
        ('wind', 'Wind Warning'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='weather_alerts')
    field_log = models.ForeignKey(FieldLog, on_delete=models.CASCADE, related_name='alerts', null=True, blank=True)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.alert_type} alert for {self.user.email}"