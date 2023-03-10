# Generated by Django 4.1.7 on 2023-02-27 18:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_bot', '0010_alter_subscription_options_alter_task_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='status',
            field=models.CharField(choices=[('WAIT', 'Ожидает принятия'), ('WORK', 'В работе'), ('WAIT_CONFIRM', 'Ожидает подтверждения'), ('DONE', 'Завершена')], default='WAIT', max_length=50, verbose_name='статус'),
        ),
    ]
