from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Habit, HabitLog, ScheduleItem, Task, UserPreference


class PlannerFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="diamondra", password="MyweekPass12345")
        self.other_user = User.objects.create_user(username="micka", password="MyweekPass12345")
        self.client.force_login(self.user)

    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_signup_creates_user_preference_and_logs_user_in(self):
        self.client.logout()
        response = self.client.post(
            reverse("signup"),
            {
                "username": "nouveau",
                "first_name": "Nouveau",
                "email": "nouveau@example.com",
                "password1": "MyweekPass67890",
                "password2": "MyweekPass67890",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        user = User.objects.get(username="nouveau")
        self.assertTrue(UserPreference.objects.filter(user=user, display_name="Nouveau").exists())

    def test_task_can_be_created_and_marked_done(self):
        response = self.client.post(
            reverse("task_add"),
            {
                "title": "Reviser DevOps",
                "description": "Chapitre Docker",
                "date": "2026-07-02",
                "priority": Task.PRIORITY_HIGH,
                "status": Task.STATUS_TODO,
                "category": "Cours",
            },
        )
        self.assertRedirects(response, reverse("tasks"))

        task = Task.objects.get(title="Reviser DevOps")
        self.assertEqual(task.user, self.user)
        response = self.client.post(reverse("task_done", args=[task.pk]))
        self.assertEqual(response.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.STATUS_DONE)

    def test_habit_toggle_creates_only_one_log_for_today(self):
        habit = Habit.objects.create(user=self.user, title="Lire", frequency=Habit.FREQUENCY_DAILY)

        self.client.post(reverse("habit_toggle", args=[habit.pk]))
        self.assertEqual(HabitLog.objects.filter(habit=habit).count(), 1)

        self.client.post(reverse("habit_toggle", args=[habit.pk]))
        self.assertEqual(HabitLog.objects.filter(habit=habit).count(), 0)

    def test_schedule_page_displays_items(self):
        ScheduleItem.objects.create(
            user=self.user,
            title="Anglais",
            subtitle="Mr Niaina",
            day=ScheduleItem.DAY_MONDAY,
            start_time=time(8, 0),
            end_time=time(12, 0),
            color="#38bdf8",
        )

        response = self.client.get(reverse("schedule"))
        self.assertContains(response, "Anglais")
        self.assertContains(response, "Mr Niaina")

    def test_schedule_page_displays_week_tasks(self):
        Task.objects.create(
            user=self.user,
            title="Preparer le rapport",
            date=date(2026, 7, 2),
            start_time=time(14, 0),
            end_time=time(15, 0),
            priority=Task.PRIORITY_HIGH,
        )
        Task.objects.create(user=self.other_user, title="Tache autre utilisateur", date=date(2026, 7, 2))

        response = self.client.get(reverse("schedule"))

        self.assertContains(response, "Preparer le rapport")
        self.assertContains(response, "14:00 - 15:00")
        self.assertNotContains(response, "Tache autre utilisateur")

    def test_schedule_page_displays_habits(self):
        Habit.objects.create(
            user=self.user,
            title="Boire de l'eau",
            frequency=Habit.FREQUENCY_DAILY,
            reminder_time=time(7, 30),
        )
        Habit.objects.create(user=self.other_user, title="Habitude autre utilisateur", frequency=Habit.FREQUENCY_DAILY)

        response = self.client.get(reverse("schedule"))

        self.assertContains(response, "Boire de l&#x27;eau", html=False)
        self.assertContains(response, "Rappel 07:30")
        self.assertNotContains(response, "Habitude autre utilisateur")

    def test_schedule_entries_are_ordered_by_time(self):
        Task.objects.create(
            user=self.user,
            title="Tache de 9h",
            date=date(2026, 7, 2),
            start_time=time(9, 0),
            priority=Task.PRIORITY_HIGH,
        )
        Habit.objects.create(
            user=self.user,
            title="Habitude de 5h",
            frequency=Habit.FREQUENCY_DAILY,
            reminder_time=time(5, 0),
        )

        response = self.client.get(reverse("schedule"))
        content = response.content.decode()

        self.assertLess(content.index("Habitude de 5h"), content.index("Tache de 9h"))

    def test_schedule_entries_at_same_time_are_split_into_lanes(self):
        Task.objects.create(
            user=self.user,
            title="Tache de 9h",
            date=date(2026, 7, 2),
            start_time=time(9, 0),
            priority=Task.PRIORITY_HIGH,
        )
        Habit.objects.create(
            user=self.user,
            title="Habitude de 9h",
            frequency=Habit.FREQUENCY_CUSTOM,
            custom_days="3",
            reminder_time=time(9, 0),
        )

        response = self.client.get(reverse("schedule"))
        content = response.content.decode()

        self.assertContains(response, "Habitude de 9h")
        self.assertContains(response, "Tache de 9h")
        self.assertIn("--lane-left: 0.0000%", content)
        self.assertIn("--lane-left: 50.0000%", content)

    def test_schedule_can_show_another_week(self):
        Task.objects.create(
            user=self.user,
            title="Tache semaine suivante",
            date=date(2026, 7, 9),
            start_time=time(10, 0),
        )

        response = self.client.get(reverse("schedule"))
        self.assertNotContains(response, "Tache semaine suivante")

        response = self.client.get(reverse("schedule"), {"week": "2026-07-09"})
        self.assertContains(response, "Tache semaine suivante")

    def test_custom_habit_days_are_respected_in_schedule(self):
        Habit.objects.create(
            user=self.user,
            title="Routine du jeudi",
            frequency=Habit.FREQUENCY_CUSTOM,
            custom_days="3",
            reminder_time=time(6, 0),
        )

        response = self.client.get(reverse("schedule"))
        content = response.content.decode()

        self.assertEqual(content.count("Routine du jeudi"), 1)

    def test_schedule_pdf_export_returns_pdf_file(self):
        Task.objects.create(
            user=self.user,
            title="Exporter cette tache",
            date=date(2026, 7, 2),
            start_time=time(9, 0),
        )

        response = self.client.get(reverse("schedule_pdf"), {"week": "2026-07-02"})
        payload = b"".join(response.streaming_content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertTrue(payload.startswith(b"%PDF"))

    def test_dashboard_displays_week_metrics(self):
        Task.objects.create(user=self.user, title="Rapport", date=date(2026, 7, 2), status=Task.STATUS_DONE)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Ta semaine")

    def test_users_do_not_see_each_other_tasks(self):
        Task.objects.create(user=self.user, title="Ma tache", date=date(2026, 7, 2))
        other_task = Task.objects.create(user=self.other_user, title="Tache cachee", date=date(2026, 7, 2))

        response = self.client.get(reverse("tasks"))
        self.assertContains(response, "Ma tache")
        self.assertNotContains(response, "Tache cachee")

        response = self.client.post(reverse("task_done", args=[other_task.pk]))
        self.assertEqual(response.status_code, 404)
