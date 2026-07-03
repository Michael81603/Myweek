from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Habit, ScheduleItem, Task, UserPreference


class DateInput(forms.DateInput):
    input_type = "date"


class TimeInput(forms.TimeInput):
    input_type = "time"


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "date",
            "start_time",
            "end_time",
            "priority",
            "status",
            "category",
            "is_important",
        ]
        widgets = {
            "date": DateInput(),
            "start_time": TimeInput(format="%H:%M"),
            "end_time": TimeInput(format="%H:%M"),
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class HabitForm(forms.ModelForm):
    custom_days = forms.MultipleChoiceField(
        label="Jours personnalises",
        choices=Habit.CUSTOM_DAY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Habit
        fields = [
            "title",
            "description",
            "frequency",
            "custom_days",
            "target_value",
            "target_unit",
            "reminder_time",
            "is_active",
        ]
        widgets = {
            "reminder_time": TimeInput(format="%H:%M"),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial["custom_days"] = self.instance.custom_days.split(",") if self.instance.custom_days else []

    def clean(self):
        cleaned_data = super().clean()
        frequency = cleaned_data.get("frequency")
        custom_days = cleaned_data.get("custom_days") or []
        if frequency == Habit.FREQUENCY_CUSTOM and not custom_days:
            self.add_error("custom_days", "Choisis au moins un jour pour une frequence personnalisee.")
        return cleaned_data

    def save(self, commit=True):
        habit = super().save(commit=False)
        habit.custom_days = ",".join(self.cleaned_data.get("custom_days") or [])
        if commit:
            habit.save()
        return habit


class ScheduleItemForm(forms.ModelForm):
    class Meta:
        model = ScheduleItem
        fields = ["title", "subtitle", "day", "start_time", "end_time", "color", "item_type"]
        widgets = {
            "start_time": TimeInput(format="%H:%M"),
            "end_time": TimeInput(format="%H:%M"),
            "color": forms.TextInput(attrs={"type": "color"}),
        }


class SettingsForm(forms.ModelForm):
    LABELS = {
        "fr": {
            "display_name": "Nom affiche",
            "language": "Langue",
            "notifications": "Notifications",
        },
        "en": {
            "display_name": "Display name",
            "language": "Language",
            "notifications": "Notifications",
        },
        "mg": {
            "display_name": "Anarana aseho",
            "language": "Fiteny",
            "notifications": "Fampandrenesana",
        },
    }

    class Meta:
        model = UserPreference
        fields = ["display_name", "language", "notifications"]

    def __init__(self, *args, language=None, **kwargs):
        super().__init__(*args, **kwargs)
        labels = self.LABELS.get(language or self.instance.language, self.LABELS["fr"])
        for field_name, label in labels.items():
            self.fields[field_name].label = label


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(label="Nom affiche", max_length=80)
    email = forms.EmailField(label="Email", required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "email", "password1", "password2"]
