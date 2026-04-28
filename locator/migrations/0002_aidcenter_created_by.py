# Generated manually for locator ownership support.

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Auth', '0003_alter_user_email_alter_user_phone_and_more'),
        ('locator', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='aidcenter',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name='aid_centers',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
