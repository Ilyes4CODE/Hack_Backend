from django.db import models

class AidCenter(models.Model):

    CENTER_TYPES = [
        ('chamber', 'Agricultural Chamber'),
        ('cooperative', 'Cooperative'),
        ('itdas', 'ITDAS Center'),
    ]

    name = models.CharField(max_length=255)
    center_type = models.CharField(max_length=20, choices=CENTER_TYPES)
    wilaya = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} — {self.wilaya}"