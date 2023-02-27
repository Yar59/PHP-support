from django.contrib import admin

from .models import Task, Subscription, User, Support, Message


class SubscriptionInline(admin.TabularInline):
    model = Subscription


class MessageFirstInline(admin.TabularInline):
    model = Message
    fk_name = "first_person"


class MessagSecondInline(admin.TabularInline):
    model = Message
    fk_name = "second_person"


class SupportionInline(admin.TabularInline):
    model = Support


@admin.register(User)
class ProductAdmin(admin.ModelAdmin):
    search_fields = [
        'name',
        'phonenumber',
        'role',
    ]
    ordering = ['name', 'role', ]

    inlines = [SubscriptionInline, MessageFirstInline, MessagSecondInline, SupportionInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    search_fields = [
        'worker',
        'client',
        'task',
        'status',
    ]
    ordering = ['status', 'task', ]
