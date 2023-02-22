from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class User(models.Model):
    class UserRole(models.TextChoices):
        CLIENT = "CL", "Клиент"
        WORKER = "WK", "Исполнитель"
        ADMIN = "ADM", "Администратор"
        MANAGER = "MNG", "Менеджер"

    role = models.CharField(
        'Роль пользователя',
        max_length=50,
        choices=UserRole.choices,
        blank=True,
        null=True,
    )

    tg_id = models.IntegerField('Telegram ID юзера')
    phonenumber = PhoneNumberField('Контактный номер', region="RU", )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.phonenumber}"


class Subscription(models.Model):
    class SubscriptionLevel(models.TextChoices):
        NOT_ACTIVE = "NA", "Не активна"
        ECONOMY = "ECO", "Экономный"
        DEFAULT = "DEFAULT", "Стандарт"
        VIP = "VIP", "ВИП"

    user = models.ForeignKey(
        'User',
        verbose_name='Пользователь',
        related_name='subscriptions',
        on_delete=models.CASCADE,
    )
    lvl = models.CharField(
        'Уровень подписки',
        max_length=50,
        choices=SubscriptionLevel.choices,
        default=SubscriptionLevel.NOT_ACTIVE
    )
    starts_at = models.DateTimeField('Начало подписки')
    end_at = models.DateTimeField('Конец подписки')

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f"{self.user} - {self.lvl}"


class Task(models.Model):
    class Proc(models.TextChoices):
        WAITING = "WAIT", "Ожидает принятия"
        IN_WORK = "WORK", "В работе"
        DONE = "DONE", "Завершена"

    status = models.CharField(
        'статус',
        max_length=50,
        choices=Proc.choices,
        default=Proc.WAITING,
    )
    client = models.ForeignKey(
        User,
        verbose_name='Клиент',
        related_name='client_tasks',
        on_delete=models.SET_NULL,
        null=True,
    )
    worker = models.ForeignKey(
        User,
        verbose_name='Исполнитель',
        related_name='worker_tasks',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    task = models.TextField('Задача')
    created_at = models.DateTimeField('Публикация задачи')
    end_at = models.DateTimeField('Конец задачи')

    class Meta:
        verbose_name = 'Задание'
        verbose_name_plural = 'Задания'

    def __str__(self):
        return f"{self.client} {self.task} {self.status}"
