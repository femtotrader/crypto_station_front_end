# Generated by Django 5.0 on 2023-12-10 21:07

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crypto_station_api", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="orders",
            name="expiration_tmstmp",
            field=models.DateTimeField(
                null=True, verbose_name="Record Expiration Timestamp"
            ),
        ),
    ]
