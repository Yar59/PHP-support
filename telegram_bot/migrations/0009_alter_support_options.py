# Generated by Django 4.1.7 on 2023-02-25 09:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_bot', '0008_alter_message_options_alter_support_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='support',
            options={'ordering': ['created_at'], 'verbose_name': 'Поддержка', 'verbose_name_plural': 'Поддержка'},
        ),
    ]