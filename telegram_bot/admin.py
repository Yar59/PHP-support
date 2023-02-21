from django.contrib import admin
from models import Status, Task, Subscription, Client, Worker


class SubscriptionInline(admin.TabularInline):
    model = Subscription


@admin.register(Client)
class ProductAdmin(admin.ModelAdmin):
    search_fields = ['phonenumber']

    inlines = [SubscriptionInline]


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    search_fields = ['phonenumber']


class StatusInline(admin.TabularInline):
    model = Status


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    search_fields = [
        'client'
        'task'
        'created_at'
        'end_at'
    ]

    inlines = [StatusInline]
