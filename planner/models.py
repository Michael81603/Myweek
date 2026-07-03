from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models
from django.utils import timezone


class Task(models.Model):
    PRIORITY_LOW = "low"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_HIGH = "high"
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "Faible"),
        (PRIORITY_MEDIUM, "Moyenne"),
        (PRIORITY_HIGH, "Importante"),
    ]

    STATUS_TODO = "todo"
    STATUS_PROGRESS = "progress"
    STATUS_DONE = "done"
    STATUS_CHOICES = [
        (STATUS_TODO, "A faire"),
        (STATUS_PROGRESS, "En cours"),
        (STATUS_DONE, "Terminee"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="tasks",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    title = models.CharField("Titre", max_length=160)
    description = models.TextField("Description", blank=True)
    date = models.DateField("Date")
    start_time = models.TimeField("Heure de debut", blank=True, null=True)
    end_time = models.TimeField("Heure de fin", blank=True, null=True)
    priority = models.CharField("Priorite", max_length=16, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    status = models.CharField("Statut", max_length=16, choices=STATUS_CHOICES, default=STATUS_TODO)
    category = models.CharField("Categorie", max_length=80, blank=True)
    is_important = models.BooleanField("Objectif important", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "start_time", "-is_important", "title"]

    def __str__(self):
        return self.title

    @property
    def is_done(self):
        return self.status == self.STATUS_DONE

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError("L'heure de fin doit etre apres l'heure de debut.")


class Habit(models.Model):
    FREQUENCY_DAILY = "daily"
    FREQUENCY_WEEKDAYS = "weekdays"
    FREQUENCY_WEEKLY = "weekly"
    FREQUENCY_CUSTOM = "custom"
    FREQUENCY_CHOICES = [
        (FREQUENCY_DAILY, "Tous les jours"),
        (FREQUENCY_WEEKDAYS, "Jours de semaine"),
        (FREQUENCY_WEEKLY, "Une fois par semaine"),
        (FREQUENCY_CUSTOM, "Personnalisee"),
    ]
    CUSTOM_DAY_CHOICES = [
        ("0", "Lundi"),
        ("1", "Mardi"),
        ("2", "Mercredi"),
        ("3", "Jeudi"),
        ("4", "Vendredi"),
        ("5", "Samedi"),
        ("6", "Dimanche"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="habits",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    title = models.CharField("Titre", max_length=160)
    description = models.TextField("Description", blank=True)
    frequency = models.CharField("Frequence", max_length=24, choices=FREQUENCY_CHOICES, default=FREQUENCY_DAILY)
    custom_days = models.CharField("Jours personnalises", max_length=32, blank=True)
    target_value = models.PositiveIntegerField("Objectif", default=1)
    target_unit = models.CharField("Unite", max_length=40, blank=True, default="fois")
    reminder_time = models.TimeField("Rappel", blank=True, null=True)
    is_active = models.BooleanField("Active", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def done_on(self, date=None):
        target_date = date or timezone.localdate()
        return self.logs.filter(date=target_date, is_done=True).exists()

    def custom_day_indexes(self):
        if not self.custom_days:
            return []
        return [int(day) for day in self.custom_days.split(",") if day.isdigit()]


class HabitLog(models.Model):
    habit = models.ForeignKey(Habit, related_name="logs", on_delete=models.CASCADE)
    date = models.DateField(default=timezone.localdate)
    is_done = models.BooleanField(default=True)
    value_done = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["habit", "date"], name="one_habit_log_per_day"),
        ]
        ordering = ["-date", "habit__title"]

    def __str__(self):
        return f"{self.habit} - {self.date}"


class ScheduleItem(models.Model):
    DAY_MONDAY = 0
    DAY_TUESDAY = 1
    DAY_WEDNESDAY = 2
    DAY_THURSDAY = 3
    DAY_FRIDAY = 4
    DAY_SATURDAY = 5
    DAY_SUNDAY = 6
    DAY_CHOICES = [
        (DAY_MONDAY, "Lundi"),
        (DAY_TUESDAY, "Mardi"),
        (DAY_WEDNESDAY, "Mercredi"),
        (DAY_THURSDAY, "Jeudi"),
        (DAY_FRIDAY, "Vendredi"),
        (DAY_SATURDAY, "Samedi"),
        (DAY_SUNDAY, "Dimanche"),
    ]

    TYPE_COURSE = "course"
    TYPE_WORK = "work"
    TYPE_PERSONAL = "personal"
    TYPE_OTHER = "other"
    TYPE_CHOICES = [
        (TYPE_COURSE, "Cours"),
        (TYPE_WORK, "Travail"),
        (TYPE_PERSONAL, "Personnel"),
        (TYPE_OTHER, "Autre"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="schedule_items",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    title = models.CharField("Titre", max_length=160)
    subtitle = models.CharField("Details", max_length=160, blank=True)
    day = models.PositiveSmallIntegerField("Jour", choices=DAY_CHOICES)
    start_time = models.TimeField("Heure de debut")
    end_time = models.TimeField("Heure de fin")
    color = models.CharField("Couleur", max_length=20, default="#22C55E")
    item_type = models.CharField("Type", max_length=24, choices=TYPE_CHOICES, default=TYPE_OTHER)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["day", "start_time", "title"]

    def __str__(self):
        return self.title

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError("L'heure de fin doit etre apres l'heure de debut.")


class UserPreference(models.Model):
    LANGUAGE_FRENCH = "fr"
    LANGUAGE_MALAGASY = "mg"
    LANGUAGE_ENGLISH = "en"
    LANGUAGE_CHOICES = [
        (LANGUAGE_FRENCH, "Francais"),
        (LANGUAGE_MALAGASY, "Malagasy"),
        (LANGUAGE_ENGLISH, "English"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="preference", on_delete=models.CASCADE)
    display_name = models.CharField("Nom affiche", max_length=80)
    language = models.CharField("Langue", max_length=8, choices=LANGUAGE_CHOICES, default=LANGUAGE_FRENCH)
    notifications = models.BooleanField("Notifications", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return self.display_name
