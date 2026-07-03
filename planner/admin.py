from django.contrib import admin

from .models import Habit, HabitLog, ScheduleItem, Task, UserPreference


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "date", "start_time", "priority", "status", "is_important")
    list_filter = ("priority", "status", "is_important", "date", "user")
    search_fields = ("title", "description", "category")


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "frequency", "target_value", "target_unit", "is_active")
    list_filter = ("frequency", "is_active", "user")
    search_fields = ("title", "description")


@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    list_display = ("habit", "date", "is_done", "value_done")
    list_filter = ("date", "is_done")


@admin.register(ScheduleItem)
class ScheduleItemAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "day", "start_time", "end_time", "item_type")
    list_filter = ("day", "item_type", "user")
    search_fields = ("title", "subtitle")


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "language", "notifications")
    search_fields = ("display_name", "user__username", "user__email")
