# Generated by Django 2.2.2 on 2019-06-05 10:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flexible_payments', '0004_auto_20190604_1551'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='external_reference',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]
