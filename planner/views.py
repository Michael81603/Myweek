from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Count
from django.http import FileResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import HabitForm, ScheduleItemForm, SettingsForm, SignUpForm, TaskForm
from .models import Habit, HabitLog, ScheduleItem, Task, UserPreference
from .pdf import build_schedule_pdf
from .services import build_week_schedule, parse_week_anchor, week_bounds, week_days


def user_preference(user):
    preference, _ = UserPreference.objects.get_or_create(
        user=user,
        defaults={"display_name": user.first_name or user.username},
    )
    return preference


def safe_next_url(request, fallback):
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return reverse(fallback)


def initial_from_query(request, fields):
    return {field: request.GET[field] for field in fields if request.GET.get(field)}


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        messages.success(request, "Connexion reussie.")
        return redirect(request.GET.get("next") or "dashboard")

    return render(request, "planner/login.html", {"form": form})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        UserPreference.objects.create(
            user=user,
            display_name=form.cleaned_data["first_name"] or user.username,
        )
        login(request, user)
        messages.success(request, "Compte cree. Bienvenue dans MyWeek.")
        return redirect("dashboard")

    return render(request, "planner/signup.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "Tu es deconnecte.")
    return redirect("login")


@login_required
def dashboard(request):
    today = timezone.localdate()
    week_start, week_end = week_bounds(today)
    preference = user_preference(request.user)
    week_tasks = Task.objects.filter(user=request.user, date__range=(week_start, week_end))
    today_tasks = Task.objects.filter(user=request.user, date=today)
    active_habits = Habit.objects.filter(user=request.user, is_active=True)
    today_logs = HabitLog.objects.filter(habit__user=request.user, date=today, is_done=True)
    habit_rows = [{"habit": habit, "done": habit.done_on(today)} for habit in active_habits[:8]]
    next_task = (
        Task.objects.filter(user=request.user, date__gte=today)
        .exclude(status=Task.STATUS_DONE)
        .order_by("date", "start_time", "-is_important")
        .first()
    )

    context = {
        "active_page": "dashboard",
        "display_name": preference.display_name,
        "today": today,
        "stats": {
            "planned": week_tasks.count(),
            "done": week_tasks.filter(status=Task.STATUS_DONE).count(),
            "habits_done": today_logs.count(),
            "important": week_tasks.filter(is_important=True).count(),
        },
        "next_task": next_task,
        "today_tasks": today_tasks,
        "habit_rows": habit_rows,
    }
    return render(request, "planner/dashboard.html", context)


@login_required
def task_list(request):
    tasks = Task.objects.filter(user=request.user)
    status = request.GET.get("status")
    priority = request.GET.get("priority")
    if status:
        tasks = tasks.filter(status=status)
    if priority:
        tasks = tasks.filter(priority=priority)

    return render(
        request,
        "planner/tasks.html",
        {
            "active_page": "tasks",
            "tasks": tasks,
            "status_choices": Task.STATUS_CHOICES,
            "priority_choices": Task.PRIORITY_CHOICES,
        },
    )


@login_required
def task_form(request, pk=None):
    task = get_object_or_404(Task, pk=pk, user=request.user) if pk else None
    initial = initial_from_query(request, ["date", "start_time", "end_time"])
    form = TaskForm(request.POST or None, instance=task, initial=initial)
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.user = request.user
        task.save()
        messages.success(request, "Tache enregistree.")
        return HttpResponseRedirect(safe_next_url(request, "tasks"))
    return render(
        request,
        "planner/form.html",
        {"active_page": "tasks", "form": form, "title": "Tache", "next_url": request.GET.get("next")},
    )


@login_required
@require_POST
def task_done(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.status = Task.STATUS_DONE
    task.save(update_fields=["status", "updated_at"])
    messages.success(request, "Tache terminee.")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("tasks")))


@login_required
@require_POST
def task_delete(request, pk):
    get_object_or_404(Task, pk=pk, user=request.user).delete()
    messages.success(request, "Tache supprimee.")
    return redirect("tasks")


@login_required
def habit_list(request):
    today = timezone.localdate()
    habits = Habit.objects.filter(user=request.user, is_active=True)
    rows = [{"habit": habit, "done": habit.done_on(today)} for habit in habits]
    return render(request, "planner/habits.html", {"active_page": "habits", "rows": rows, "today": today})


@login_required
def habit_form(request, pk=None):
    habit = get_object_or_404(Habit, pk=pk, user=request.user) if pk else None
    initial = initial_from_query(request, ["frequency", "reminder_time"])
    if request.GET.get("custom_days"):
        initial["custom_days"] = request.GET.getlist("custom_days")
    form = HabitForm(request.POST or None, instance=habit, initial=initial)
    if request.method == "POST" and form.is_valid():
        habit = form.save(commit=False)
        habit.user = request.user
        habit.save()
        messages.success(request, "Habitude enregistree.")
        return HttpResponseRedirect(safe_next_url(request, "habits"))
    return render(
        request,
        "planner/form.html",
        {"active_page": "habits", "form": form, "title": "Habitude", "next_url": request.GET.get("next")},
    )


@login_required
@require_POST
def habit_toggle(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user, is_active=True)
    today = timezone.localdate()
    log = HabitLog.objects.filter(habit=habit, date=today).first()
    if log:
        log.delete()
        messages.info(request, "Habitude decochee pour aujourd'hui.")
    else:
        HabitLog.objects.create(habit=habit, date=today, is_done=True, value_done=habit.target_value)
        messages.success(request, "Habitude cochee pour aujourd'hui.")
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("habits")))


@login_required
@require_POST
def habit_delete(request, pk):
    get_object_or_404(Habit, pk=pk, user=request.user).delete()
    messages.success(request, "Habitude supprimee.")
    return redirect("habits")


@login_required
def schedule(request):
    schedule_context = build_week_schedule(request.user, parse_week_anchor(request.GET.get("week")))
    return render(
        request,
        "planner/schedule.html",
        {"active_page": "schedule", "schedule_next_url": request.get_full_path(), **schedule_context},
    )


@login_required
def schedule_pdf(request):
    schedule_context = build_week_schedule(request.user, parse_week_anchor(request.GET.get("week")))
    pdf = build_schedule_pdf(schedule_context, request.user)
    filename = f"myweek-emploi-du-temps-{schedule_context['week_start']:%Y-%m-%d}.pdf"
    return FileResponse(pdf, as_attachment=True, filename=filename, content_type="application/pdf")


@login_required
def schedule_form(request, pk=None):
    item = get_object_or_404(ScheduleItem, pk=pk, user=request.user) if pk else None
    initial = initial_from_query(request, ["day", "start_time", "end_time"])
    form = ScheduleItemForm(request.POST or None, instance=item, initial=initial)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.user = request.user
        item.save()
        messages.success(request, "Activite enregistree.")
        return HttpResponseRedirect(safe_next_url(request, "schedule"))
    return render(
        request,
        "planner/form.html",
        {"active_page": "schedule", "form": form, "title": "Activite", "next_url": request.GET.get("next")},
    )


@login_required
@require_POST
def schedule_delete(request, pk):
    get_object_or_404(ScheduleItem, pk=pk, user=request.user).delete()
    messages.success(request, "Activite supprimee.")
    return redirect("schedule")


@login_required
def statistics(request):
    today = timezone.localdate()
    week_start, week_end = week_bounds(today)
    tasks = Task.objects.filter(user=request.user, date__range=(week_start, week_end))
    done_tasks = tasks.filter(status=Task.STATUS_DONE).count()
    total_tasks = tasks.count()
    logs = HabitLog.objects.filter(habit__user=request.user, date__range=(week_start, week_end), is_done=True)
    best_habit = logs.values("habit__title").annotate(total=Count("id")).order_by("-total").first()

    daily = []
    for day in week_days(today):
        daily.append(
            {
                "label": day["label"],
                "tasks": tasks.filter(date=day["date"], status=Task.STATUS_DONE).count(),
                "habits": logs.filter(date=day["date"]).count(),
            }
        )

    productivity = round((done_tasks / total_tasks) * 100) if total_tasks else 0
    return render(
        request,
        "planner/statistics.html",
        {
            "active_page": "statistics",
            "total_tasks": total_tasks,
            "done_tasks": done_tasks,
            "habit_logs": logs.count(),
            "productivity": productivity,
            "best_habit": best_habit,
            "daily": daily,
        },
    )


@login_required
def settings_view(request):
    preference = user_preference(request.user)
    form_language = request.POST.get("language") if request.method == "POST" else preference.language
    form = SettingsForm(request.POST or None, instance=preference, language=form_language)
    if request.method == "POST" and "reset" in request.POST:
        Task.objects.filter(user=request.user).delete()
        Habit.objects.filter(user=request.user).delete()
        ScheduleItem.objects.filter(user=request.user).delete()
        messages.success(request, "Tes donnees ont ete reinitialisees.")
        return redirect("dashboard")
    if request.method == "POST" and form.is_valid():
        preference = form.save()
        request.session["myweek_language"] = preference.language
        messages.success(request, "Parametres enregistres.")
        return redirect("settings")
    return render(request, "planner/settings.html", {"active_page": "settings", "form": form})
