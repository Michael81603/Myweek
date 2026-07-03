from datetime import date, time, timedelta

from django.utils import timezone

from .models import Habit, HabitLog, ScheduleItem, Task


SCHEDULE_START_HOUR = 5
SCHEDULE_END_HOUR = 23
DEFAULT_TASK_DURATION = 45
DEFAULT_HABIT_DURATION = 30
MIN_ENTRY_DURATION = 30


def week_bounds(day=None):
    current = day or timezone.localdate()
    start = current - timedelta(days=current.weekday())
    return start, start + timedelta(days=6)


def week_days(day=None):
    start, _ = week_bounds(day)
    labels = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    return [{"index": i, "label": labels[i], "date": start + timedelta(days=i)} for i in range(7)]


def parse_week_anchor(value):
    if not value:
        return timezone.localdate()
    try:
        return date.fromisoformat(value)
    except ValueError:
        return timezone.localdate()


def habit_occurs_on(habit, day):
    if habit.frequency == Habit.FREQUENCY_WEEKDAYS:
        return day.weekday() < 5
    if habit.frequency == Habit.FREQUENCY_WEEKLY:
        return day.weekday() == 0
    if habit.frequency == Habit.FREQUENCY_CUSTOM:
        return day.weekday() in habit.custom_day_indexes()
    return True


def minutes_from_schedule_start(value):
    if value is None:
        return None
    raw_minutes = value.hour * 60 + value.minute - SCHEDULE_START_HOUR * 60
    max_minutes = (SCHEDULE_END_HOUR - SCHEDULE_START_HOUR) * 60 - MIN_ENTRY_DURATION
    return max(0, min(raw_minutes, max_minutes))


def duration_minutes(start_time, end_time, default):
    if not start_time or not end_time:
        return default
    start_total = start_time.hour * 60 + start_time.minute
    end_total = end_time.hour * 60 + end_time.minute
    return max(MIN_ENTRY_DURATION, end_total - start_total)


def sort_schedule_entries(entries):
    return sorted(
        entries,
        key=lambda entry: (
            entry["sort_time"] is None,
            entry["sort_time"] or time.max,
            entry["rank"],
            entry["title"].lower(),
        ),
    )


def assign_same_time_lanes(entries):
    entries_by_start = {}
    for entry in entries:
        entries_by_start.setdefault(entry["start_minutes"], []).append(entry)

    for group in entries_by_start.values():
        lane_count = len(group)
        for lane_index, entry in enumerate(group):
            entry["lane_left"] = f"{lane_index * 100 / lane_count:.4f}%"
            entry["lane_width"] = f"{100 / lane_count:.4f}%"

    return entries


def split_schedule_entries(entries):
    ordered = sort_schedule_entries(entries)
    timed = [entry for entry in ordered if entry["sort_time"] is not None]
    return {
        "timed": assign_same_time_lanes(timed),
        "unscheduled": [entry for entry in ordered if entry["sort_time"] is None],
    }


def activity_entry(item):
    return {
        "kind": "activity",
        "activity": item,
        "sort_time": item.start_time,
        "start_minutes": minutes_from_schedule_start(item.start_time),
        "duration_minutes": duration_minutes(item.start_time, item.end_time, 60),
        "rank": 1,
        "title": item.title,
    }


def task_entry(task):
    return {
        "kind": "task",
        "task": task,
        "sort_time": task.start_time,
        "start_minutes": minutes_from_schedule_start(task.start_time),
        "duration_minutes": duration_minutes(task.start_time, task.end_time, DEFAULT_TASK_DURATION),
        "rank": 3,
        "title": task.title,
    }


def habit_entry(habit, day, done_habits, today):
    return {
        "kind": "habit",
        "habit": habit,
        "done": (habit.pk, day) in done_habits,
        "is_today": day == today,
        "sort_time": habit.reminder_time,
        "start_minutes": minutes_from_schedule_start(habit.reminder_time),
        "duration_minutes": DEFAULT_HABIT_DURATION,
        "rank": 2,
        "title": habit.title,
    }


def build_week_schedule(user, anchor_date=None):
    today = timezone.localdate()
    week_start, week_end = week_bounds(anchor_date or today)
    days = week_days(week_start)
    entries_by_day = {day["index"]: [] for day in days}

    for item in ScheduleItem.objects.filter(user=user):
        entries_by_day[item.day].append(activity_entry(item))

    tasks = Task.objects.filter(user=user, date__range=(week_start, week_end))
    for task in tasks:
        entries_by_day[task.date.weekday()].append(task_entry(task))

    habits = Habit.objects.filter(user=user, is_active=True).order_by("reminder_time", "title")
    habit_logs = HabitLog.objects.filter(habit__user=user, date__range=(week_start, week_end), is_done=True)
    done_habits = {(log.habit_id, log.date) for log in habit_logs}

    for day in days:
        day_date = day["date"]
        for habit in habits:
            if habit_occurs_on(habit, day_date):
                entries_by_day[day["index"]].append(habit_entry(habit, day_date, done_habits, today))

    columns = []
    for day in days:
        split_entries = split_schedule_entries(entries_by_day[day["index"]])
        columns.append(
            {
                "day": day,
                "timed_entries": split_entries["timed"],
                "unscheduled_entries": split_entries["unscheduled"],
            }
        )

    return {
        "columns": columns,
        "hour_rows": [
            {
                "hour": hour,
                "label": f"{hour:02d}:00",
                "value": f"{hour:02d}:00",
                "next_value": f"{hour + 1:02d}:00",
                "start_minutes": (hour - SCHEDULE_START_HOUR) * 60,
            }
            for hour in range(SCHEDULE_START_HOUR, SCHEDULE_END_HOUR)
        ],
        "week_start": week_start,
        "week_end": week_end,
        "previous_week": week_start - timedelta(days=7),
        "next_week": week_start + timedelta(days=7),
        "current_week": week_bounds(today)[0],
    }
