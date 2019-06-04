# Generated by Django 2.2.1 on 2019-05-30 12:28

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.FLEXIBLE_PLANS_CUSTOMER_MODEL),
        migrations.swappable_dependency(settings.FLEXIBLE_PLANS_PLAN_MODEL),
        migrations.swappable_dependency(settings.FLEXIBLE_PLANS_SUBSCRIPTION_MODEL),
        ('flexible_payments', '0002_auto_20190515_1413'),
    ]

    operations = [
        migrations.CreateModel(
            name='BraintreePaymentMethod',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('flexible_payments.paymentmethod',),
            managers=[
                ('object', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='BraintreeSubscription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, null=True)),
                ('subscription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.FLEXIBLE_PLANS_SUBSCRIPTION_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='BraintreePlan',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, null=True)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.FLEXIBLE_PLANS_PLAN_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='BraintreeCustomer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, null=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.FLEXIBLE_PLANS_CUSTOMER_MODEL)),
            ],
        ),
    ]