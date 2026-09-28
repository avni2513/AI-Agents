"""Interactive AI Timetable Agent.

Ask for a full-week timetable in plain English, e.g.

    Plan a full week timetable: college 9 to 4 Mon-Fri, gym 4 times,
    study 2 hours daily

then keep talking to refine it - move things around, add activities, block
out time, ask "what's on Friday?" - across multiple turns.

Two modes, chosen automatically:

  1. AI mode      - if `anthropic` is installed AND ANTHROPIC_API_KEY is
                    set, you get a genuinely free-form chat with Claude,
                    which remembers the whole conversation. You can ask
                    things like "plan a full week timetable for me".
  2. Offline mode - otherwise (or if an AI request ever fails), a
                    command-driven fallback builds a real weekly timetable
                    from a one-line request (like the example above) or a short
                    setup, and lets you adjust it with commands.
                    Type 'help' once inside it to see the command list.

Setup for AI mode:
    pip install anthropic
    export ANTHROPIC_API_KEY="sk-ant-..."

Run:
    python3 timetable_agent.py
"""

from __future__ import annotations

import json
import math
import os
import re
import textwrap
from dataclasses import dataclass, field
from typing import Optional

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

# Override via env var if your account needs a different alias/snapshot.
# Check docs.claude.com for current model IDs.
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")


def normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def ask(prompt: str) -> str:
    """Optional field: blank is a valid answer."""
    return input(f"{prompt}: ").strip()


def ask_with_default(prompt: str, default: str) -> str:
    """Used only for things like file names, where a shown default is genuinely convenient."""
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


# ----------------------------------------------------------------------
# Time and day helpers
# ----------------------------------------------------------------------

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WORK_DAYS = DAYS[:5]

_DAY_ALIASES: dict[str, str] = {}
for _d in DAYS:
    _DAY_ALIASES[_d.lower()] = _d
    _DAY_ALIASES[_d.lower()[:3]] = _d
_DAY_ALIASES.update({"tues": "Tuesday", "weds": "Wednesday", "thur": "Thursday", "thurs": "Thursday"})


def resolve_days(token: str) -> Optional[list[str]]:
    token = normalize(token)
    if token in {"everyday", "every day", "daily", "all", "everyday."}:
        return list(DAYS)
    if token in {"weekdays", "weekday"}:
        return list(WORK_DAYS)
    if token in {"weekends", "weekend"}:
        return DAYS[5:]
    day = _DAY_ALIASES.get(token)
    return [day] if day else None


def parse_time(text: str) -> Optional[int]:
    """Parses '7', '7:30', '07:30', '6pm', '6:15 am' into minutes after midnight."""
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", normalize(text))
    if not m:
        return None
    hour, minute, suffix = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if suffix:
        if not (1 <= hour <= 12):
            return None
        hour = hour % 12 + (12 if suffix == "pm" else 0)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour * 60 + minute


def ask_time_required(prompt: str) -> int:
    while True:
        value = parse_time(input(f"{prompt}: "))
        if value is not None:
            return value
        print("  (please enter a time like 7:00, 06:30 or 11pm)")


def fmt_time(minutes: int) -> str:
    minutes %= 1440
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def fmt_duration(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    return f"{h}h" if h else f"{m}m"


def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


# ======================================================================
# AI mode - free-form multi-turn chat
# ======================================================================

AI_CHAT_SYSTEM_PROMPT = """You are a practical, friendly timetable planner having an ongoing \
conversation with a person who wants to organise their time. Ask clarifying questions if \
you're missing key details (wake and sleep times, fixed commitments like classes or work, \
subjects or goals with rough weekly hours, meal times, preferred study or work hours, days \
off). Once you have enough to work with, produce a complete Monday-to-Sunday timetable in \
plain text, one day per section, with one line per block in the form "07:00-07:45  Morning \
routine". Include meals, breaks, rest and free time, not just tasks, and keep the load \
realistic - never schedule someone from dawn to midnight without breaks. When the person \
asks for changes (move something, add an activity, make a day lighter, free up an evening), \
revise the plan and restate only the days that changed unless asked to restate everything. \
You can also answer questions about the current timetable ("what do I have on Friday?", \
"how many hours of maths this week?"). Keep responses well-organised and readable in plain \
text (short headers, no markdown tables)."""


def _extract_text(response) -> str:
    return "\n".join(block.text for block in response.content if getattr(block, "type", "") == "text")


def run_ai_mode() -> None:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    messages: list[dict] = []

    print("\nTimetable Agent (AI mode) - tell me what you need planned.")
    print("Commands: 'save' to save the conversation, 'help' for tips, 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHave a well-organised week!")
            return
        if not user_input:
            continue

        low = normalize(user_input)
        if low in {"exit", "quit", "bye"}:
            print("Have a well-organised week!")
            return
        if low == "help":
            print(
                "\nJust talk naturally, e.g.:\n"
                "  'Plan a full week timetable for me: college 9 to 4 Mon-Fri, gym 4 times, study 2 hours daily'\n"
                "  'Make Wednesday lighter'\n"
                "  'Move gym to mornings'\n"
                "  'Add a weekend hobby slot'\n"
                "  'What do I have on Friday?'\n"
                "Type 'save' to save the conversation to a text file, 'exit' to quit.\n"
            )
            continue
        if low == "save":
            _save_transcript(messages)
            continue

        messages.append({"role": "user", "content": user_input})
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=2500,
                system=AI_CHAT_SYSTEM_PROMPT,
                messages=messages,
            )
            reply_text = _extract_text(response)
        except Exception as exc:  # noqa: BLE001 - any failure should fall back, not crash
            print(f"\nAI request failed ({exc}).")
            print("Switching to offline mode for the rest of this session.\n")
            run_offline_mode()
            return

        messages.append({"role": "assistant", "content": reply_text})
        print(f"\nPlanner: {reply_text}\n")


def _save_transcript(messages: list[dict]) -> None:
    if not messages:
        print("Nothing to save yet.")
        return
    filename = ask_with_default("File name", "timetable_conversation.txt")
    with open(filename, "w", encoding="utf-8") as f:
        for m in messages:
            speaker = "You" if m["role"] == "user" else "Planner"
            f.write(f"{speaker}: {m['content']}\n\n")
    print(f"Saved conversation to {filename}")


# ======================================================================
# Offline mode - command-driven, no API key needed, always works
# ======================================================================

@dataclass
class Prefs:
    wake: int = 7 * 60
    sleep: int = 23 * 60                       # stored as time of day; may be after midnight
    work: Optional[tuple[int, int]] = None      # fixed block, e.g. college or office
    work_days: list[str] = field(default_factory=lambda: list(WORK_DAYS))
    activities: dict[str, float] = field(default_factory=dict)   # name -> hours per week
    # Optional scheduling rules per activity, e.g. {"Study": {"days": [...], "sessions": None, "minutes": 120}}
    patterns: dict[str, dict] = field(default_factory=dict)
    blocks: list[dict] = field(default_factory=list)             # {"day", "start", "end", "label"}
    variant: int = 0                            # bumped by 'shuffle' to get a different layout
    # Per-day edits ("make monday lighter", "no gym on monday", "move gym to friday", ...)
    skip: dict[str, set[str]] = field(default_factory=dict)      # activity -> days it must avoid
    day_cap: dict[str, int] = field(default_factory=dict)        # day -> max activity minutes
    pins: list[dict] = field(default_factory=list)               # sessions forced onto a day
    work_off: set[str] = field(default_factory=set)              # days with no work/college
    pref: dict[str, str] = field(default_factory=dict)           # activity -> morning/afternoon/evening


_DEFAULT_ACTIVITIES = {"Study": 10.0, "Exercise": 3.0, "Hobby time": 3.0, "Chores & errands": 3.0}
_MAX_SESSION_MIN = 90
_BREAK_MIN = 15


def day_end(prefs: Prefs) -> int:
    """End of the waking day in minutes; adds 24h when sleep is after midnight."""
    return prefs.sleep if prefs.sleep > prefs.wake else prefs.sleep + 1440


def _valid_day_length(wake: int, sleep: int) -> bool:
    end = sleep if sleep > wake else sleep + 1440
    return end - wake >= 6 * 60


def parse_activities(raw: str) -> dict[str, float]:
    """Parses 'maths 5, physics:4, gym 3 hours' into {'Maths': 5.0, ...}."""
    result: dict[str, float] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        m = re.match(r"^(.+?)[:\s]+(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hours?)?$", item, re.IGNORECASE)
        if m:
            name, hours = m.group(1).strip(), float(m.group(2))
        else:
            name, hours = item, 2.0
        if name and hours > 0:
            result[name[0].upper() + name[1:]] = hours
    return result


def _find_activity(prefs: Prefs, name: str) -> Optional[str]:
    for existing in prefs.activities:
        if existing.lower() == name.lower():
            return existing
    return None


# ---- Timetable building --------------------------------------------------

def _try_add(slots: list[dict], lo: int, hi: int, start: int, end: int, label: str, kind: str) -> bool:
    start, end = max(start, lo), min(end, hi)
    if end <= start:
        return False
    if any(_overlaps(start, end, s["start"], s["end"]) for s in slots):
        return False
    slots.append({"start": start, "end": end, "label": label, "kind": kind})
    return True


def _free_windows(slots: list[dict], lo: int, hi: int) -> list[tuple[int, int]]:
    windows: list[tuple[int, int]] = []
    cursor = lo
    for s in sorted(slots, key=lambda x: x["start"]):
        if s["start"] > cursor:
            windows.append((cursor, s["start"]))
        cursor = max(cursor, s["end"])
    if cursor < hi:
        windows.append((cursor, hi))
    return windows


def _find_slot(slots: list[dict], lo: int, hi: int, dur: int, pref: Optional[str] = None) -> Optional[int]:
    """First start time where `dur` minutes fit, preferring morning/afternoon/evening if asked."""
    rng = {"morning": (lo, 12 * 60), "afternoon": (12 * 60, 17 * 60), "evening": (17 * 60, hi)}.get(pref or "")
    for use_pref in ((True, False) if rng else (False,)):
        for gap in (_BREAK_MIN, 0):          # keep a short break between sessions if there is room
            for ws, we in _free_windows(slots, lo, hi):
                start = ws
                if gap and any(s["kind"] == "activity" and s["end"] == ws for s in slots):
                    start = ws + gap
                if use_pref and rng:
                    start = max(start, rng[0])
                    if start >= rng[1]:
                        continue
                if start + dur <= we:
                    return start
    return None


def _split_sessions(hours: float) -> list[int]:
    total = int(round(hours * 60))
    if total <= 0:
        return []
    count = max(1, math.ceil(total / _MAX_SESSION_MIN))
    each = max(5, int(round(total / count / 5)) * 5)
    return [each] * count


def _split_for_day(minutes: int) -> list[int]:
    """One block per day, split in two only if it is longer than 2 hours."""
    if minutes <= 120:
        return [minutes]
    count = math.ceil(minutes / 120)
    return [max(5, int(round(minutes / count / 5)) * 5)] * count


def build_timetable(prefs: Prefs) -> dict:
    lo, hi = prefs.wake, day_end(prefs)
    warnings: list[str] = []
    table: dict[str, list[dict]] = {}

    # 1) Fixed things first: work/college, then the person's own blocks, then routine.
    for day in DAYS:
        slots: list[dict] = []
        if prefs.work and day in prefs.work_days and day not in prefs.work_off:
            _try_add(slots, lo, hi, prefs.work[0], prefs.work[1], "Work / college", "work")
        for b in prefs.blocks:
            if b["day"] == day and not _try_add(slots, lo, hi, b["start"], b["end"], b["label"], "block"):
                warnings.append(f"'{b['label']}' on {day} overlaps something else and was skipped.")
        _try_add(slots, lo, hi, lo, lo + 45, "Wake up, morning routine & breakfast", "routine")
        _try_add(slots, lo, hi, hi - 30, hi, "Wind down & get ready for bed", "routine")
        _try_add(slots, lo, hi, 13 * 60, 14 * 60, "Lunch", "meal")
        _try_add(slots, lo, hi, 20 * 60, 21 * 60, "Dinner", "meal")
        table[day] = slots

    # 2) Turn each activity into sessions, honouring per-day edits. Sessions tied to
    #    particular days go first, then flexible ones are interleaved to keep days varied.
    Session = tuple[str, int, Optional[list[str]], bool, Optional[str]]   # name, minutes, days, pinned, pref
    fixed: list[Session] = []
    queues: dict[str, list[tuple[int, Optional[list[str]]]]] = {}
    for name, hours in prefs.activities.items():
        skipped = prefs.skip.get(name, set())
        pat = prefs.patterns.get(name)
        if pat and pat.get("sessions") is None and pat.get("days"):
            for d in pat["days"]:
                if d in skipped:
                    continue
                for part in _split_for_day(pat["minutes"]):
                    fixed.append((name, part, [d], False, prefs.pref.get(name)))
        elif pat and pat.get("sessions"):
            allowed = [d for d in (pat.get("days") or DAYS) if d not in skipped]
            queues[name] = [(pat["minutes"], allowed)] * pat["sessions"]
        else:
            allowed = [d for d in DAYS if d not in skipped] if skipped else None
            queues[name] = [(dur, allowed) for dur in _split_sessions(hours)]

    pinned: list[Session] = []
    for pin in prefs.pins:
        name = pin["name"]
        if name not in prefs.activities:
            continue
        if pin.get("counts") and queues.get(name):
            queues[name].pop()          # a moved session replaces one flexible session
        pinned.append((name, pin["minutes"], [pin["day"]], True, pin.get("pref") or prefs.pref.get(name)))

    flexible: list[Session] = []
    while any(queues.values()):
        for name, q in queues.items():
            if q:
                dur, allowed = q.pop(0)
                flexible.append((name, dur, allowed, False, prefs.pref.get(name)))
    sessions = pinned + fixed + flexible

    # 3) Place each session on the least-loaded allowed day that has room.
    load = {d: 0 for d in DAYS}
    unscheduled: list[dict] = []
    for name, dur, allowed, is_pin, pref in sessions:
        def key(d: str, name: str = name) -> tuple[int, int, int]:
            same = any(s["label"] == name for s in table[d])
            return (int(same), load[d], (DAYS.index(d) + prefs.variant) % 7)

        placed = False
        capped_fixed = False
        candidates = DAYS if allowed is None else allowed
        for day in sorted(candidates, key=key):
            use = dur
            cap = None if is_pin else prefs.day_cap.get(day)
            if cap is not None and cap - load[day] < dur:
                shrunk = ((cap - load[day]) // 5) * 5
                if allowed is not None and len(allowed) == 1 and shrunk >= 30:
                    use = shrunk                    # a lighter day shortens the session
                else:
                    capped_fixed = capped_fixed or (allowed is not None and len(allowed) == 1)
                    continue
            start = _find_slot(table[day], lo, hi, use, pref)
            if start is not None:
                table[day].append({"start": start, "end": start + use, "label": name, "kind": "activity"})
                load[day] += use
                placed = True
                break
        if not placed and not capped_fixed:
            unscheduled.append({"activity": name, "minutes": dur})

    return {"timetable": table, "unscheduled": unscheduled, "warnings": warnings}


# ---- Plain-English request parsing -----------------------------------------

_TIME = r"\d{1,2}(?::\d{2})?\s*(?:am|pm)?"
_WORK_WORDS = r"(?:college|university|uni|work|school|office|classes|class|job|lectures?|shift)"
_FILLER_PREFIX = re.compile(
    r"^(?:(?:and|also|plus|with|where|including|include|add|i want|i need|i'd like|i have|to|do|go to|go)\s+)+"
)
_PLAN_VERB = re.compile(
    r"^(?:(?:please|can you|could you|i want you to|i want to|i need to|help me)\s+)*"
    r"(?:plan|make|create|build|generate|prepare|design|set up|give me)\b"
)
_PLAN_NOUN = re.compile(r"\b(?:week|weekly|timetable|schedule|routine)\b")


def find_days(text: str, allow_daily: bool = False) -> Optional[list[str]]:
    """Finds day words in text: weekdays, weekends, ranges like 'mon-fri', or single days."""
    text = normalize(text)
    if re.search(r"\bweekdays?\b", text):
        return list(WORK_DAYS)
    if re.search(r"\bweekends?\b", text):
        return DAYS[5:]
    if allow_daily and re.search(r"\b(?:daily|every ?day|each day|a day|per day|all week)\b", text):
        return list(DAYS)
    m = re.search(r"\b([a-z]{3,9})\s*(?:-|to|through|till|until)\s*([a-z]{3,9})\b", text)
    if m and m.group(1) in _DAY_ALIASES and m.group(2) in _DAY_ALIASES:
        a = DAYS.index(_DAY_ALIASES[m.group(1)])
        b = DAYS.index(_DAY_ALIASES[m.group(2)])
        return [DAYS[(a + i) % 7] for i in range((b - a) % 7 + 1)]
    found: list[str] = []
    for w in re.findall(r"[a-z]+", text):
        d = _DAY_ALIASES.get(w)
        if d and d not in found:
            found.append(d)
    return found or None


def fmt_days(days: list[str]) -> str:
    if days == DAYS:
        return "every day"
    if days == WORK_DAYS:
        return "Mon-Fri"
    if days == DAYS[5:]:
        return "Sat-Sun"
    return ", ".join(d[:3] for d in days)


def _infer_range(start_text: str, end_text: str) -> Optional[tuple[int, int]]:
    """Reads '9 to 4' as 09:00-16:00 by assuming the end is in the afternoon when needed."""
    s, e = parse_time(start_text), parse_time(end_text)
    if s is None or e is None:
        return None
    has_s = bool(re.search(r"[ap]m", start_text))
    has_e = bool(re.search(r"[ap]m", end_text))
    if not has_s and not has_e and s < 6 * 60:
        s += 12 * 60
    if e <= s and not has_e:
        e += 12 * 60
    if e <= s or e >= 1440:
        return None
    return s, e


def _clean_name(raw: str) -> str:
    name = _FILLER_PREFIX.sub("", raw.strip()).strip(" .")
    return (name[0].upper() + name[1:]) if name else ""


def _to_minutes(value: float, unit: str) -> int:
    return int(round(value * 60)) if unit.startswith("h") else int(round(value))


def _split_plan_request(msg: str) -> Optional[str]:
    """If msg is a 'plan my week ...' request, returns the details after the request phrase
    (possibly empty). Returns None when msg is not a plan request."""
    if not _PLAN_VERB.match(msg) or not _PLAN_NOUN.search(msg):
        return None
    if ":" in msg:
        head, body = msg.split(":", 1)
        if _PLAN_NOUN.search(head):
            return body.strip()
    m = re.match(
        r"^.*?\b(?:week|weekly|timetable|schedule|routine)\b(?:\s+(?:timetable|schedule|routine|plan))*"
        r"(?:\s+for me)?\s*(?:with|where|including|that has|having|,|-)?\s*(.*)$",
        msg,
    )
    return m.group(1).strip() if m else ""


def apply_plan_request(body: str, prefs: Prefs) -> tuple[bool, list[str]]:
    """Reads details like 'college 9 to 4 mon-fri, gym 4 times, study 2 hours daily'
    and updates prefs. Returns (understood_anything, notes)."""
    notes: list[str] = []
    new_work: Optional[tuple[int, int]] = None
    new_work_days: list[str] = list(WORK_DAYS)
    new_acts: dict[str, float] = {}
    new_patterns: dict[str, dict] = {}
    new_wake: Optional[int] = None
    new_sleep: Optional[int] = None
    ignored: list[str] = []

    for seg in re.split(r"\s*(?:,|;|&|\band\b|\bplus\b)\s*", normalize(body)):
        seg = seg.strip(" .!")
        if not seg:
            continue

        m = re.match(rf"^(?:i )?(?:wake(?: up)?|get up)(?: at| by| around)?\s*({_TIME})$", seg)
        if m and parse_time(m.group(1)) is not None:
            new_wake = parse_time(m.group(1))
            continue
        m = re.match(rf"^(?:i )?(?:sleep|go to bed|go to sleep|bed ?time|bed)(?: at| by| around| is)?\s*({_TIME})$", seg)
        if m and parse_time(m.group(1)) is not None:
            new_sleep = parse_time(m.group(1))
            continue

        m = re.match(
            rf"^(?:i have |have )?({_WORK_WORDS})\b(?:\s+(?:from|at|is))?\s*({_TIME})\s*(?:-|to|till|until)\s*({_TIME})\b(.*)$",
            seg,
        )
        if m:
            rng = _infer_range(m.group(2).strip(), m.group(3).strip())
            if rng:
                new_work = rng
                new_work_days = find_days(m.group(4)) or list(WORK_DAYS)
                continue

        m = re.match(r"^(.+?)\s+(\d+)\s*(?:x|times?|sessions?|days?)\b(.*)$", seg)
        if m:
            name, count, tail = _clean_name(m.group(1)), int(m.group(2)), m.group(3)
            if name and 1 <= count <= 14:
                minutes, assumed = 60, True
                d = re.search(r"\bfor\s+(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)\b", tail)
                if d:
                    minutes, assumed = _to_minutes(float(d.group(1)), d.group(2)), False
                allowed = find_days(tail)
                new_acts[name] = round(count * minutes / 60, 2)
                new_patterns[name] = {"days": allowed, "sessions": count, "minutes": minutes}
                extra = f" on {fmt_days(allowed)}" if allowed else ""
                notes.append(f"{name}: {count} session(s) a week{extra}, {fmt_duration(minutes)} each"
                             + (" (length assumed)" if assumed else ""))
                continue

        m = re.match(r"^(.+?)\s+(?:for\s+)?(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)\b\s*(.*)$", seg)
        if m:
            name, amount, unit, tail = _clean_name(m.group(1)), float(m.group(2)), m.group(3), m.group(4)
            if name and amount > 0:
                minutes = _to_minutes(amount, unit)
                weekly = re.search(r"\b(?:a week|per week|weekly|each week|in a week)\b", tail)
                days = None if weekly else find_days(tail, allow_daily=True)
                if days:
                    new_acts[name] = round(minutes * len(days) / 60, 2)
                    new_patterns[name] = {"days": days, "sessions": None, "minutes": minutes}
                    notes.append(f"{name}: {fmt_duration(minutes)} on {fmt_days(days)} "
                                 f"({new_acts[name]:g}h per week)")
                else:
                    new_acts[name] = round(minutes / 60, 2)
                    notes.append(f"{name}: {new_acts[name]:g}h per week")
                continue

        ignored.append(seg)

    if new_work:
        prefs.work, prefs.work_days = new_work, new_work_days
        notes.insert(0, f"College/work: {fmt_time(new_work[0])}-{fmt_time(new_work[1])}, {fmt_days(new_work_days)}")
    if new_work or new_acts:
        _clear_edits(prefs)
    if new_acts:
        prefs.activities, prefs.patterns = new_acts, new_patterns
    wake = new_wake if new_wake is not None else prefs.wake
    sleep = new_sleep if new_sleep is not None else prefs.sleep
    if (new_wake is not None or new_sleep is not None):
        if _valid_day_length(wake, sleep):
            prefs.wake, prefs.sleep = wake, sleep
            notes.append(f"Wake {fmt_time(wake)}, bed {fmt_time(sleep)}")
        else:
            notes.append("Ignored the wake/bed times because they leave fewer than 6 waking hours")
    for seg in ignored:
        notes.append(f"Couldn't understand: '{seg}'")

    understood = bool(new_work or new_acts or new_wake is not None or new_sleep is not None)
    return understood, notes


# ---- Setup ---------------------------------------------------------------

def collect_prefs() -> Prefs:
    print("Let's set up your week.\n")
    while True:
        wake = ask_time_required("Wake-up time (e.g. 6:30)")
        sleep = ask_time_required("Bedtime (e.g. 23:00)")
        if _valid_day_length(wake, sleep):
            break
        print("  (that leaves fewer than 6 waking hours - please re-enter)")

    prefs = Prefs(wake=wake, sleep=sleep)

    while True:
        raw = ask("Fixed Mon-Fri work/college hours, e.g. 9-17 - optional")
        if not raw:
            break
        m = re.match(r"^(.+?)\s*(?:-|to)\s*(.+)$", raw)
        start = parse_time(m.group(1)) if m else None
        end = parse_time(m.group(2)) if m else None
        if start is not None and end is not None and end > start:
            prefs.work = (start, end)
            break
        print("  (please use a range like 9-17 or 9am-5pm, or leave blank)")

    raw = ask("Activities with weekly hours, e.g. maths 5, physics 4, gym 3 - optional")
    prefs.activities = parse_activities(raw) or dict(_DEFAULT_ACTIVITIES)
    return prefs


def collect_prefs_from_request() -> Optional[Prefs]:
    """Lets the person describe the week in one sentence; falls back to step-by-step questions."""
    print("Tell me what to plan, for example:")
    print("  Plan a full week timetable: college 9 to 4 Mon-Fri, gym 4 times, study 2 hours daily")
    print("(or just press Enter for step-by-step questions)\n")
    try:
        raw = input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if normalize(raw) in {"exit", "quit", "bye"}:
        return None
    if raw:
        low = normalize(raw).rstrip("?.!")
        body = _split_plan_request(low)
        prefs = Prefs()
        understood, notes = apply_plan_request(low if body is None else body, prefs)
        if understood:
            if not prefs.activities:
                prefs.activities = dict(_DEFAULT_ACTIVITIES)
                notes.append("No activities given, so I added a few defaults (see 'show activities')")
            print("\nHere's what I understood:")
            for n in notes:
                print(f"  - {n}")
            print(f"  - Assuming wake {fmt_time(prefs.wake)} and bed {fmt_time(prefs.sleep)} "
                  "(change with 'set wake 6:30' / 'set sleep 23:00')")
            return prefs
        print("\nI couldn't pick out the details, so let's do it step by step.\n")
    return collect_prefs()


# ---- Display helpers -----------------------------------------------------

def _day_rows(state: dict, prefs: Prefs, day: str) -> list[dict]:
    lo, hi = prefs.wake, day_end(prefs)
    slots = state["timetable"][day]
    rows = list(slots)
    for ws, we in _free_windows(slots, lo, hi):
        if we - ws >= 30:
            rows.append({"start": ws, "end": we, "label": "Free time", "kind": "free"})
    return sorted(rows, key=lambda r: r["start"])


def format_day(state: dict, prefs: Prefs, day: str) -> str:
    lines = [day.upper(), "-" * 60]
    for r in _day_rows(state, prefs, day):
        lines.append(f"  {fmt_time(r['start'])}-{fmt_time(r['end'])}  {r['label']}")
    return "\n".join(lines)


def scheduled_minutes(state: dict) -> dict[str, int]:
    totals: dict[str, int] = {}
    for slots in state["timetable"].values():
        for s in slots:
            if s["kind"] == "activity":
                totals[s["label"]] = totals.get(s["label"], 0) + (s["end"] - s["start"])
    return totals


def format_activities(state: dict, prefs: Prefs) -> str:
    totals = scheduled_minutes(state)
    lines = ["ACTIVITIES (target vs scheduled per week)", "-" * 60]
    if not prefs.activities:
        lines.append("  (none yet - try 'add gym 3 hours')")
    for name, hours in prefs.activities.items():
        extra = sum(p["minutes"] for p in prefs.pins if p["name"] == name and not p.get("counts")) / 60
        lines.append(f"  {name:<24} target {hours + extra:g}h   scheduled {fmt_duration(totals.get(name, 0))}")
    if prefs.day_cap or prefs.skip or prefs.pins or prefs.work_off:
        lines.append("\n  (Some days have edits, so scheduled can differ from target - see 'show changes'.)")
    if state["unscheduled"]:
        lines.append("\n  Could not fit:")
        for u in state["unscheduled"]:
            lines.append(f"    - {u['activity']} ({fmt_duration(u['minutes'])} session): "
                         "try fewer hours, an earlier wake time or a later bedtime")
    return "\n".join(lines)


def format_blocks(prefs: Prefs) -> str:
    lines = ["FIXED BLOCKS", "-" * 60]
    if prefs.work:
        lines.append(f"  {fmt_days(prefs.work_days):<9} {fmt_time(prefs.work[0])}-{fmt_time(prefs.work[1])}  Work / college")
    for b in prefs.blocks:
        lines.append(f"  {b['day']:<9} {fmt_time(b['start'])}-{fmt_time(b['end'])}  {b['label']}")
    if len(lines) == 2:
        lines.append("  (none - try 'block friday 18:00-20:00 movie night')")
    return "\n".join(lines)


def format_warnings(state: dict) -> str:
    return "\n".join(f"  ! {w}" for w in state["warnings"])


def format_week(state: dict, prefs: Prefs) -> str:
    line = "=" * 60
    parts = [
        f"{line}\nWEEKLY TIMETABLE  (wake {fmt_time(prefs.wake)}, bed {fmt_time(prefs.sleep)})\n{line}",
    ]
    parts.extend(format_day(state, prefs, d) for d in DAYS)
    parts.append(format_activities(state, prefs))
    if state["warnings"]:
        parts.append("WARNINGS\n" + "-" * 60 + "\n" + format_warnings(state))
    parts.append(line)
    return "\n\n".join(parts)


def save_to_file(state: dict, prefs: Prefs, path: str) -> None:
    export = {
        "wake": fmt_time(prefs.wake),
        "bedtime": fmt_time(prefs.sleep),
        "activities_hours_per_week": prefs.activities,
        "timetable": {
            day: [
                {"start": fmt_time(r["start"]), "end": fmt_time(r["end"]), "label": r["label"], "kind": r["kind"]}
                for r in _day_rows(state, prefs, day)
            ]
            for day in DAYS
        },
        "unscheduled": state["unscheduled"],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(export, f, indent=2, ensure_ascii=False)
    print(f"Saved full timetable to {path}")


# ---- Command handling ----------------------------------------------------

OFFLINE_HELP = textwrap.dedent("""
    Things you can ask or do:
      plan a full week timetable: college 9 to 4 Mon-Fri, gym 4 times, study 2 hours daily
                                                  - describe your week in plain English
                                                    (also: wake at 6:30, sleep at 11pm,
                                                    maths 5 hours a week, reading 30 min daily)
      plan my week                                - rebuild the whole week
      shuffle                                     - a different arrangement
      show week / show monday / what's on friday  - view the plan
      when is gym                                 - see when an activity happens
      show activities / show blocks / show changes - targets vs scheduled / fixed blocks / edits
      Change one day (day can be monday, mon-wed, weekdays, weekends...):
        make monday lighter                       - about half the activities that day
        free monday                               - no activities that day
        no gym on monday                          - skip an activity on a day
        move gym from monday to friday evening    - move one session
        move gym to mornings                      - prefer a time of day for an activity
        add study 2 hours on saturday             - extra session on a day
        monday off / no college on monday         - no work or college that day
        reset monday / reset all                  - undo those edits
      add gym 3 hours                             - add an activity (hours per week)
      change gym to 4 hours                       - change its weekly hours
      remove gym                                  - remove an activity
      block friday 18:00-20:00 movie night        - fixed block (day can be weekdays,
                                                    weekends or everyday too)
      unblock movie night                         - remove a fixed block
      set work 9-17 / remove work                 - Mon-Fri work or college hours
      set wake 6:30 / set sleep 23:00             - change wake or bed time
      save                                        - save the timetable to a JSON file
      help                                        - show this again
      exit                                        - quit
""").strip()


def _rebuild(prefs: Prefs, state: dict) -> None:
    state.update(build_timetable(prefs))


def _with_warnings(text: str, state: dict) -> str:
    if state["warnings"]:
        return text + "\n\nWarnings:\n" + format_warnings(state)
    return text


def handle_offline_command(message: str, prefs: Prefs, state: dict) -> Optional[str]:
    """Returns a response string, or None if the command wasn't recognized."""
    msg = normalize(message).rstrip("?.!")

    # --- viewing ---
    if msg in {"show week", "show timetable", "show schedule", "show plan", "show everything",
               "show all", "show", "week"}:
        return format_week(state, prefs)
    if msg in {"show activities", "list activities", "show subjects", "show summary", "summary"}:
        return format_activities(state, prefs)
    if msg in {"show blocks", "list blocks"}:
        return format_blocks(prefs)

    words = re.findall(r"[a-z]+", msg)
    if words and words[0] in {"show", "what", "whats", "what's", "display", "see", "view"}:
        for w in words[1:]:
            if w in _DAY_ALIASES:
                return format_day(state, prefs, _DAY_ALIASES[w])

    m = re.match(r"^when (?:is|are|do i have|do i do|do i study|will i do) (?:my )?(.+)$", msg)
    if m:
        name = _find_activity(prefs, m.group(1).strip())
        if not name:
            return f"'{m.group(1).strip()}' isn't in your activities. Type 'show activities' to see them."
        lines = [f"{name.upper()} THIS WEEK", "-" * 60]
        for day in DAYS:
            for s in sorted(state["timetable"][day], key=lambda x: x["start"]):
                if s["kind"] == "activity" and s["label"] == name:
                    lines.append(f"  {day:<10} {fmt_time(s['start'])}-{fmt_time(s['end'])}")
        if len(lines) == 2:
            lines.append("  (nothing scheduled - it may not have fit; see 'show activities')")
        return "\n".join(lines)

    # --- plain-English plan requests ---
    body = _split_plan_request(msg)
    if body:
        understood, notes = apply_plan_request(body, prefs)
        if understood or notes:
            _rebuild(prefs, state)
            text = "Here's what I understood:\n" + "\n".join(f"  - {n}" for n in notes)
            return _with_warnings(text + "\n\n" + format_week(state, prefs), state)

    # --- rebuilding ---
    if msg in {"shuffle", "regenerate", "replan", "rebuild", "another version"}:
        prefs.variant += 1
        _rebuild(prefs, state)
        return _with_warnings("Rearranged the week.\n\n" + format_week(state, prefs), state)
    if re.search(r"\b(plan|make|create|build|generate|redo|prepare)\b.*\b(week|weekly|timetable|schedule)\b", msg):
        _rebuild(prefs, state)
        return _with_warnings(format_week(state, prefs), state)

    # --- per-day edits: "make monday lighter", "no gym on monday", "move gym to friday" ... ---
    edit = _handle_day_edits(msg, prefs, state)
    if edit is not None:
        return edit

    # --- settings: wake, sleep, work ---
    m = re.match(r"^(?:set|change) (wake|sleep)(?: up)?(?: time)?(?: to| at)? (.+)$", msg)
    if m:
        value = parse_time(m.group(2))
        if value is None:
            return "I couldn't read that time. Try something like 6:30 or 11pm."
        wake = value if m.group(1) == "wake" else prefs.wake
        sleep = value if m.group(1) == "sleep" else prefs.sleep
        if not _valid_day_length(wake, sleep):
            return "That would leave fewer than 6 waking hours, so I didn't change it."
        prefs.wake, prefs.sleep = wake, sleep
        _rebuild(prefs, state)
        return _with_warnings(f"Wake {fmt_time(prefs.wake)}, bed {fmt_time(prefs.sleep)}.\n\n"
                              + format_week(state, prefs), state)

    m = re.match(r"^(?:set|change) (?:work|college|school|office)(?: hours| time)?(?: to)? (.+?)\s*(?:-|to)\s*(.+)$", msg)
    if m:
        start, end = parse_time(m.group(1)), parse_time(m.group(2))
        if start is None or end is None or end <= start:
            return "I couldn't read that range. Try 'set work 9-17' or 'set work 9am-5pm'."
        prefs.work, prefs.work_days = (start, end), list(WORK_DAYS)
        _rebuild(prefs, state)
        return _with_warnings(f"Work set to {fmt_time(start)}-{fmt_time(end)} on weekdays.\n\n"
                              + format_week(state, prefs), state)

    if re.match(r"^(?:remove|delete|no|clear) (?:work|college|school|office)(?: hours)?$", msg):
        prefs.work = None
        _rebuild(prefs, state)
        return "Removed the weekday work/college block.\n\n" + format_week(state, prefs)

    # --- fixed blocks ---
    m = re.match(r"^block (\S+) (\S+?)\s*(?:-|to)\s*(\S+) (.+)$", msg)
    if m:
        days = resolve_days(m.group(1))
        start, end = parse_time(m.group(2)), parse_time(m.group(3))
        label = m.group(4).strip()
        if not days:
            return "I didn't recognise that day. Use a day name, 'weekdays', 'weekends' or 'everyday'."
        if start is None or end is None or end <= start:
            return "I couldn't read that time range. Try 'block friday 18:00-20:00 movie night'."
        label = label[0].upper() + label[1:]
        for d in days:
            prefs.blocks.append({"day": d, "start": start, "end": end, "label": label})
        _rebuild(prefs, state)
        return _with_warnings(f"Blocked {fmt_time(start)}-{fmt_time(end)} for '{label}'.\n\n"
                              + format_week(state, prefs), state)

    m = re.match(r"^(?:unblock|remove block|delete block) (.+)$", msg)
    if m:
        target = m.group(1).strip()
        before = len(prefs.blocks)
        prefs.blocks = [b for b in prefs.blocks if target not in b["label"].lower()]
        if len(prefs.blocks) == before:
            return f"No fixed block matching '{target}'. Type 'show blocks' to see them."
        _rebuild(prefs, state)
        return _with_warnings(f"Removed blocks matching '{target}'.\n\n" + format_week(state, prefs), state)

    # --- activities ---
    m = re.match(r"^(?:change|set|update) (.+?) (?:to |as )?(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hours?)?(?: (?:a|per) week)?$", msg)
    if m:
        name = _find_activity(prefs, m.group(1).strip())
        if not name:
            return f"'{m.group(1).strip()}' isn't in your activities. Use 'add {m.group(1).strip()} 3 hours' first."
        hours = float(m.group(2))
        if hours <= 0:
            return "Use 'remove <name>' to drop an activity."
        prefs.activities[name] = hours
        prefs.patterns.pop(name, None)
        _rebuild(prefs, state)
        return _with_warnings(f"{name} is now {hours:g}h per week.\n\n" + format_week(state, prefs), state)

    m = re.match(r"^add (?:an? )?(?:activity |subject |task )?(.+?) (\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hours?)?(?: (?:a|per) week)?$", msg)
    if m:
        raw_name, hours = m.group(1).strip(), float(m.group(2))
        if hours <= 0:
            return "Please give a number of hours greater than 0."
        name = _find_activity(prefs, raw_name) or (raw_name[0].upper() + raw_name[1:])
        prefs.activities[name] = hours
        prefs.patterns.pop(name, None)
        _rebuild(prefs, state)
        return _with_warnings(f"{name} set to {hours:g}h per week.\n\n" + format_week(state, prefs), state)

    m = re.match(r"^(?:remove|delete|drop) (?:activity |subject |task )?(.+)$", msg)
    if m:
        name = _find_activity(prefs, m.group(1).strip())
        if not name:
            return f"'{m.group(1).strip()}' isn't in your activities. Type 'show activities' to see them."
        del prefs.activities[name]
        prefs.patterns.pop(name, None)
        prefs.skip.pop(name, None)
        prefs.pref.pop(name, None)
        prefs.pins = [p for p in prefs.pins if p["name"] != name]
        _rebuild(prefs, state)
        return _with_warnings(f"Removed {name}.\n\n" + format_week(state, prefs), state)

    if msg == "help":
        return OFFLINE_HELP

    # Mentions a day but isn't a known command: show that day and explain how to change it.
    days = find_days(msg)
    if days and len(days) <= 3:
        return "\n\n".join(format_day(state, prefs, d) for d in days) + "\n\n" + _day_edit_tips(days[0])

    return None


# ---- Per-day edits ---------------------------------------------------------

_LIGHT_WORDS = (r"(?:lighter|easier|more relaxed|relaxed|less busy|less packed|less hectic|"
                r"quieter|calmer|chill|not so busy)")
_TIME_OF_DAY = re.compile(r"\b(morning|afternoon|evening|night)s?\b")


def _pref_of(text: str) -> Optional[str]:
    m = _TIME_OF_DAY.search(text)
    if not m:
        return None
    return "evening" if m.group(1) == "night" else m.group(1)


def _strip_pref(text: str) -> str:
    text = _TIME_OF_DAY.sub("", text)
    return normalize(re.sub(r"\b(?:in|during|the|at)\b", " ", text))


def _clear_edits(prefs: Prefs) -> None:
    prefs.skip.clear()
    prefs.day_cap.clear()
    prefs.pins.clear()
    prefs.work_off.clear()
    prefs.pref.clear()


def _clear_day_edits(prefs: Prefs, days: list[str]) -> None:
    for d in days:
        prefs.day_cap.pop(d, None)
        prefs.work_off.discard(d)
        for name in list(prefs.skip):
            prefs.skip[name].discard(d)
            if not prefs.skip[name]:
                del prefs.skip[name]
    prefs.pins = [p for p in prefs.pins if p["day"] not in days]


def _activity_minutes_on(state: dict, day: str) -> int:
    return sum(s["end"] - s["start"] for s in state["timetable"][day] if s["kind"] == "activity")


def _day_edit_tips(day: str) -> str:
    d = day.lower()
    return (f"To change {day}, try:\n"
            f"  - make {d} lighter          - free {d}          - {d} off (no college/work)\n"
            f"  - no gym on {d}             - move gym from {d} to friday evening\n"
            f"  - add study 2 hours on {d} evening\n"
            f"  - reset {d}                 - undo edits for that day")


def format_changes(prefs: Prefs) -> str:
    lines = ["CHANGES YOU'VE MADE", "-" * 60]
    for day in DAYS:
        parts: list[str] = []
        if day in prefs.work_off:
            parts.append("no college/work")
        cap = prefs.day_cap.get(day)
        if cap == 0:
            parts.append("no activities")
        elif cap is not None:
            parts.append(f"light (max {fmt_duration(cap)} of activities)")
        parts.extend(f"no {n}" for n, days in prefs.skip.items() if day in days)
        for p in prefs.pins:
            if p["day"] == day:
                when = f" ({p['pref']})" if p.get("pref") else ""
                parts.append(f"{p['name']} {fmt_duration(p['minutes'])}{when}"
                             + (" (moved here)" if p.get("counts") else " (extra)"))
        if parts:
            lines.append(f"  {day:<10} " + ", ".join(parts))
    lines.extend(f"  {n}: prefers {p}s" for n, p in prefs.pref.items())
    if len(lines) == 2:
        lines.append("  (none yet - try 'make monday lighter' or 'no gym on monday')")
    return "\n".join(lines)


def _finish(prefs: Prefs, state: dict, message: str, days: list[str]) -> str:
    _rebuild(prefs, state)
    shown = "\n\n".join(format_day(state, prefs, d) for d in days) if len(days) <= 3 else format_week(state, prefs)
    text = message + "\n\n" + shown
    if state["unscheduled"]:
        text += "\n\nNote: some sessions didn't fit anywhere (see 'show activities')."
    return _with_warnings(text, state)


def _handle_day_edits(msg: str, prefs: Prefs, state: dict) -> Optional[str]:
    """Handles edits aimed at particular days. Returns None if msg isn't one of them."""
    # -- show / reset
    if msg in {"show changes", "show edits", "list changes"}:
        return format_changes(prefs)
    if msg in {"reset", "reset all", "reset changes", "reset all changes", "undo all changes", "revert all changes"}:
        _clear_edits(prefs)
        return _finish(prefs, state, "Cleared all day-by-day changes.", DAYS)
    m = re.match(r"^(?:reset|undo|revert|restore|undo changes (?:for|on)|clear changes (?:for|on)) (?:the )?(.+)$", msg)
    if m:
        days = find_days(m.group(1))
        if days:
            _clear_day_edits(prefs, days)
            return _finish(prefs, state, f"Reset {', '.join(days)} to the normal plan.", days)

    # -- lighter day
    m = (re.match(rf"^(?:make|keep|set|change) (?:the )?(.+?)(?:'s)?(?: day| schedule| timetable)? "
                  rf"(?:a bit |a little |much |way )?{_LIGHT_WORDS}$", msg)
         or re.match(r"^lighten (?:up )?(?:the )?(.+)$", msg))
    if m:
        days = find_days(m.group(1))
        if days:
            notes = []
            for d in days:
                load = _activity_minutes_on(state, d)
                if load == 0:
                    notes.append(f"{d} has no activities to lighten.")
                    continue
                prefs.day_cap[d] = max(0, int(round(load / 2 / 15)) * 15)
                notes.append(f"{d} is now capped at {fmt_duration(prefs.day_cap[d])} of activities.")
            return _finish(prefs, state, " ".join(notes), days)

    # -- free day
    m = (re.match(r"^(?:free|clear|empty)(?: up| out)? (?:the )?(.+?)(?:'s)?(?: day| schedule| timetable)?$", msg)
         or re.match(r"^keep (?:the )?(.+?) free$", msg)
         or re.match(r"^(?:no|skip) (?:activities|tasks|everything|anything|studying) (?:on|for) (.+)$", msg))
    if m:
        days = find_days(m.group(1))
        if days:
            for d in days:
                prefs.day_cap[d] = 0
            return _finish(prefs, state, f"{', '.join(days)}: no activities.", days)

    # -- no work/college on a day
    m = (re.match(r"^(?:no|skip|cancel|remove|delete) (?:the )?(?:work|college|school|office|classes|class|job|"
                  r"university|uni|lectures?) (?:on|for|from) (.+)$", msg)
         or re.match(r"^(?:take |make |have )?(?:the )?(.+?)(?: a)? (?:off|holiday|day off)$", msg))
    if m:
        days = find_days(m.group(1))
        if days:
            if not prefs.work:
                return "You haven't set any work or college hours yet. Try 'set work 9-17'."
            prefs.work_off.update(days)
            return _finish(prefs, state, f"No college/work on {', '.join(days)}. "
                                         "(Say 'free <day>' to clear the activities too.)", days)

    # -- move an activity (to another day, or to a time of day)
    m = re.match(r"^(?:move|shift|reschedule) (?:the )?(.+?)(?: sessions?)?(?: from (.+?))? to (.+)$", msg)
    if m:
        name = _find_activity(prefs, m.group(1).strip())
        dest_text = m.group(3).strip()
        if name:
            dest_days = find_days(dest_text)
            pref = _pref_of(dest_text)
            if not dest_days and pref:
                prefs.pref[name] = pref
                return _finish(prefs, state, f"{name} will be placed in the {pref} where possible.", DAYS)
            if dest_days:
                if len(dest_days) != 1:
                    return "Please name one day to move it to, e.g. 'move gym to friday'."
                dest = dest_days[0]
                sessions = [(d, s) for d in DAYS for s in state["timetable"][d]
                            if s["kind"] == "activity" and s["label"] == name]
                if m.group(2):
                    src_days = find_days(m.group(2))
                    if not src_days or len(src_days) != 1:
                        return "Please name one day to move it from, e.g. 'move gym from monday to friday'."
                    src = src_days[0]
                elif len(sessions) == 1:
                    src = sessions[0][0]
                else:
                    where = ", ".join(sorted({d[:3] for d, _ in sessions})) or "nowhere yet"
                    return (f"{name} happens on {where}. Say which one, e.g. "
                            f"'move {name.lower()} from {sessions[0][0].lower() if sessions else 'monday'} to {dest.lower()}'.")
                match = next((s for d, s in sessions if d == src), None)
                if not match:
                    return f"There's no {name} on {src} to move."
                if any(d == dest for d, _ in sessions):
                    return f"{name} is already on {dest}."
                minutes = match["end"] - match["start"]
                moved_here = next((p for p in prefs.pins if p["name"] == name and p["day"] == src), None)
                if moved_here:
                    prefs.pins.remove(moved_here)
                prefs.skip.setdefault(name, set()).add(src)
                prefs.skip[name].discard(dest)
                prefs.pins.append({"day": dest, "name": name, "minutes": minutes, "counts": True, "pref": pref})
                return _finish(prefs, state, f"Moved {name} from {src} to {dest}"
                                             + (f" ({pref})." if pref else "."), [src, dest])

    # -- add an extra session on a day
    m = re.match(r"^add (?:an? )?(.+?)(?: (\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m))? (?:on|for) (.+)$", msg)
    if m:
        pref = _pref_of(m.group(4))
        days = find_days(_strip_pref(m.group(4)))
        if days:
            raw = m.group(1).strip()
            minutes = _to_minutes(float(m.group(2)), m.group(3)) if m.group(2) else 60
            name = _find_activity(prefs, raw) or (raw[0].upper() + raw[1:])
            if name not in prefs.activities:
                prefs.activities[name] = 0.0
            for d in days:
                prefs.pins.append({"day": d, "name": name, "minutes": minutes, "counts": False, "pref": pref})
                if name in prefs.skip:
                    prefs.skip[name].discard(d)
            return _finish(prefs, state, f"Added {name} ({fmt_duration(minutes)}) on {', '.join(days)}.", days)

    # -- skip an activity on certain days
    m = re.match(r"^(?:no|skip|cancel|drop|remove|delete) (?:the )?(.+?) (?:on|from|for) (.+)$", msg)
    if m:
        days = find_days(m.group(2))
        raw = m.group(1).strip()
        if days and not raw.startswith("block"):
            name = _find_activity(prefs, raw)
            if not name:
                return f"'{raw}' isn't in your activities. Type 'show activities' to see them."
            prefs.skip.setdefault(name, set()).update(days)
            prefs.pins = [p for p in prefs.pins if not (p["name"] == name and p["day"] in days)]
            return _finish(prefs, state, f"No {name} on {', '.join(days)}.", days)

    return None


def run_offline_mode() -> None:
    if not _ANTHROPIC_AVAILABLE:
        print("\n(`anthropic` package not installed - running in offline mode.)")
    elif not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n(No ANTHROPIC_API_KEY set - running in offline mode.)")

    prefs = collect_prefs_from_request()
    if prefs is None:
        return
    state: dict = {}
    _rebuild(prefs, state)
    print()
    print(format_week(state, prefs))
    print("\nYou can now chat to adjust the timetable. Type 'help' to see commands, 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHave a well-organised week!")
            return
        if not user_input:
            continue

        low = normalize(user_input)
        if low in {"exit", "quit", "bye"}:
            print("Have a well-organised week!")
            return
        if low == "save":
            filename = ask_with_default("File name", "weekly_timetable.json")
            save_to_file(state, prefs, filename)
            continue

        response = handle_offline_command(user_input, prefs, state)
        if response is None:
            response = "I didn't recognize that command. Type 'help' to see what I can do."
        print(f"\nPlanner:\n{response}\n")


# ======================================================================
# Main
# ======================================================================

def main() -> None:
    print("=" * 60)
    print("INTERACTIVE STUDY AGENT")
    print("=" * 60)

    use_ai = _ANTHROPIC_AVAILABLE and bool(os.environ.get("ANTHROPIC_API_KEY"))
    if use_ai:
        run_ai_mode()
    else:
        run_offline_mode()


if __name__ == "__main__":
    main()