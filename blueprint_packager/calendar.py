"""Turn "Week 4, last day, 11:59 p.m. Eastern" into the timestamp a package carries.

The blueprint speaks in weeks and weekdays. A term calendar in the build
settings supplies the dates of each week. This module joins the two and
nothing else: it does not read prose, guess a term, or assume a time zone
offset. Daylight-saving changes are handled by the zone database, so a term
that crosses one gets the right offset on each side.

Package timestamps are UTC in the form Brightspace accepted from the MBA 630
build: ``2026-11-09T04:59:00.000Z``.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
LAST_DAY = "last_day"
FIRST_DAY = "first_day"


class CalendarError(ValueError):
    pass


class Calendar:
    def __init__(self, spec: dict[str, Any]) -> None:
        for key in ("timezone", "weeks"):
            if key not in spec:
                raise CalendarError(f"The calendar needs '{key}'")
        self.zone_name = spec["timezone"]
        self.zone = ZoneInfo(self.zone_name)
        self.weeks: dict[int, tuple[date, date]] = {}
        for number, (start, end) in spec["weeks"].items():
            first, last = date.fromisoformat(start), date.fromisoformat(end)
            if last < first:
                raise CalendarError(f"Week {number} ends before it starts")
            self.weeks[int(number)] = (first, last)
        self.due_time = time.fromisoformat(spec.get("due_time", "23:59"))
        self.rules: dict[str, dict[str, Any]] = spec.get("rules", {})
        self.overrides: dict[str, dict[str, dict[str, Any]]] = spec.get("overrides", {})

    def day(self, week: int, which: str) -> date:
        if week not in self.weeks:
            raise CalendarError(f"The calendar has no Week {week}")
        first, last = self.weeks[week]
        if which == LAST_DAY:
            return last
        if which == FIRST_DAY:
            return first
        if which.lower() not in WEEKDAYS:
            raise CalendarError(f"Unknown day '{which}'. Use a weekday name, '{LAST_DAY}', or '{FIRST_DAY}'.")
        target = WEEKDAYS.index(which.lower())
        current = first
        while current <= last:
            if current.weekday() == target:
                return current
            current += timedelta(days=1)
        raise CalendarError(f"Week {week} runs {first} to {last} and has no {which.title()}")

    def rule(self, role: str, title: str = "") -> dict[str, Any] | None:
        """The rule for one role ("assignment", "discussion_initial", ...), with any per-activity override."""
        override = self.overrides.get(title, {}).get(role)
        return override if override is not None else self.rules.get(role)

    def due(self, role: str, week: int | None, title: str = "") -> dict[str, Any] | None:
        rule = self.rule(role, title)
        if not rule:
            return None
        week = int(rule.get("week", week if week is not None else 0))
        if not week:
            raise CalendarError(f"'{title or role}' has no week, and its rule names none")
        # a rule may name a different day for the term's last week, which is often short
        day = rule["last_week_day"] if rule.get("last_week_day") and week == max(self.weeks) else rule["day"]
        return self.stamp(week, day, rule.get("time"))

    def stamp(self, week: int, which: str, at: str | None = None) -> dict[str, Any]:
        day = self.day(week, which)
        clock = time.fromisoformat(at) if at else self.due_time
        local = datetime.combine(day, clock, tzinfo=self.zone)
        utc = local.astimezone(timezone.utc)
        hour = local.strftime("%I:%M").lstrip("0")
        return {
            "week": week,
            "weekday": WEEKDAYS[day.weekday()].title(),
            "local": local.isoformat(),
            "utc": utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "label": f"{WEEKDAYS[day.weekday()].title()}, {local.strftime('%B')} {day.day}, {day.year}, {hour} {'a.m.' if local.hour < 12 else 'p.m.'} {local.tzname()}",
            "rule": which,
        }


def utc_parts(stamp_utc: str) -> dict[str, int]:
    """Month, day, year, hour, minutes, seconds of a package timestamp, for the nested quiz form."""
    moment = datetime.strptime(stamp_utc, "%Y-%m-%dT%H:%M:%S.000Z")
    return {"month": moment.month, "day": moment.day, "year": moment.year,
            "hour": moment.hour, "minutes": moment.minute, "seconds": moment.second}
