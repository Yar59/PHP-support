# Generated by Django 4.1.7 on 2023-02-24 12:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_bot', '0003_alter_user_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='end_at',
            field=models.DateTimeField(blank=True, verbose_name='Конец задачи'),
        ),
    ]
