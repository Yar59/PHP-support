from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class User(models.Model):
    class UserRole(models.TextChoices):
        CLIENT = "1", "PUB"
        CON = "2", "CONTRACTOR"

    role = models.CharField(
        'Роль пользователя',
        max_length=50,
        choices=UserRole.choices,
    )

    tg_id = models.IntegerField('Telegram ID юзера')
    phonenumber = PhoneNumberField('Контактный номер', region="RU",)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.phonenumber}"


class Subscription(models.Model):
    user = models.ForeignKey(
        'User',
        verbose_name='Пользователь',
        related_name='subscription',
        on_delete=models.CASCADE,
    )
    lvl = models.IntegerField(verbose_name='Уровень подписки')
    starts_at = models.DateTimeField('Начало подписки')
    end_at = models.DateTimeField('Конец подписки')

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f"{self.user} - {self.lvl}"


class Task(models.Model):
    class Proc(models.TextChoices):
        PUB = "1", "PUB"
        WORK = "2", "WORK"
        DONE = "3", "DONE"

    status = models.CharField(
        'статус',
        max_length=50,
        choices=Proc.choices,
        default=Proc.PUB,
    )
    client = models.ForeignKey(
        'User',
        verbose_name='Клиент',
        related_name='tasks',
        on_delete=models.SET_NULL,
        null=True,
    )

    task = models.TextField('Задача')
    created_at = models.DateTimeField('Публикация задачи')
    end_at = models.DateTimeField('Конец задачи')

    class Meta:
        verbose_name = 'Задание'
        verbose_name_plural = 'Задания'

    def __str__(self):
        return f"{self.client} {self.task} {self.status}"
