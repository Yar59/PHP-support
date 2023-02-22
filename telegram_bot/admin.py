from django.contrib import admin

from .models import Task, Subscription, User


class SubscriptionInline(admin.TabularInline):
    model = Subscription


@admin.register(User)
class ProductAdmin(admin.ModelAdmin):
    search_fields = ['phonenumber']

    inlines = [SubscriptionInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    search_fields = [
        'client'
        'task'
        'status'
    ]
