# Generated by Django 4.1.7 on 2023-02-25 08:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_bot', '0005_alter_task_end_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(verbose_name='Дата отправки')),
                ('text', models.TextField(verbose_name='Сообщение')),
                ('first_person', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='first_messages', to='telegram_bot.user', verbose_name='Клиент')),
                ('second_person', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='second_messages', to='telegram_bot.user', verbose_name='Исполнитель')),
                ('task_message', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messages', to='telegram_bot.task', verbose_name='Задача')),
            ],
            options={
                'verbose_name': 'Задание',
                'verbose_name_plural': 'Задания',
                'ordering': ['created_at'],
            },
        ),
    ]