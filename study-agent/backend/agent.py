import re


KNOWN_SUBJECTS = [
    "computer science",
    "maths",
    "math",
    "physics",
    "chemistry",
    "biology",
    "english",
    "history",
    "geography",
    "economics",
    "accountancy",
    "science",
    "hindi",
    "civics",
    "political science",
    "business studies",
    "programming",
]


ACTIVITIES = [
    "Learn new topic",
    "Practice questions",
    "Revise notes",
    "Solve past papers",
]


def fmt(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def find_subjects(text):
    found = [
        s for s in KNOWN_SUBJECTS
        if re.search(rf"\b{re.escape(s)}\b", text)
    ]

    if "maths" in found and "math" in found:
        found.remove("math")

    if found:
        return [s.title() for s in found]

    return []


def parse_time(text):
    pattern = (
        r"\b(?:starting at|start(?:ing)? at|from|begin(?:ning)? at)"
        r"\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?"
    )

    match = re.search(pattern, text, re.I)

    if not match:
        return 9 * 60

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    suffix = match.group(3)

    if suffix and suffix.lower() == "pm" and hour < 12:
        hour += 12

    if suffix and suffix.lower() == "am" and hour == 12:
        hour = 0

    return hour * 60 + minute if hour < 24 else 9 * 60


def make_plan(text):
    subjects = find_subjects(text)

    if not subjects:
        return (
            "Which subjects should I plan for? "
            "Try: plan a 2 day timetable for maths, physics and chemistry"
        )

    days = 7 if re.search(r"\bweek\b", text) else 1

    match = re.search(r"(\d+)\s*-?\s*days?", text)

    if match:
        days = max(1, min(int(match.group(1)), 14))

    hours = 6.0

    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b", text)

    if match:
        hours = max(1.0, min(float(match.group(1)), 12.0))

    start = parse_time(text)

    blocks = max(1, int(hours * 60 // 50))

    counter = 0

    lines = [
        f"STUDY PLAN: {', '.join(subjects)} "
        f"({days} day(s), about {hours:g}h study per day, start {fmt(start)})",
        "=" * 62
    ]

    for day in range(1, days + 1):
        lines.append(f"\nDAY {day}")
        lines.append("-" * 62)

        time = start

        for i in range(blocks):
            last = (i == blocks - 1) and blocks > 2

            if last:
                lines.append(
                    f"  {fmt(time)}-{fmt(time + 50)}  "
                    "Quick revision of the day: " + ", ".join(subjects)
                )
            else:
                subject = subjects[counter % len(subjects)]
                activity = ACTIVITIES[
                    (counter // len(subjects)) % len(ACTIVITIES)
                ]

                lines.append(
                    f"  {fmt(time)}-{fmt(time + 50)}  "
                    f"{subject} - {activity}"
                )

                counter += 1

            time += 50

            if i < blocks - 1:
                if i == blocks // 2 - 1 and blocks >= 4:
                    lines.append(
                        f"  {fmt(time)}-{fmt(time + 45)}  Lunch break"
                    )
                    time += 45
                else:
                    lines.append(
                        f"  {fmt(time)}-{fmt(time + 10)}  "
                        "Short break (water, stretch)"
                    )
                    time += 10

        lines.append(
            f"  {fmt(time)}       Done! "
            "Review tomorrow's plan and sleep on time."
        )

    lines.append(
        "\nTips: put the hardest subject in your first block, "
        "keep your phone away, and adjust the plan if a topic needs more time."
    )

    return "\n".join(lines)


TOPICS = [
    (
        ["pomodoro"],
        "POMODORO TECHNIQUE\n"
        "Study for 25 minutes with full focus, then take a 5 minute break. "
        "After 4 rounds, take a 15-30 minute break."
    ),
    (
        [
            "procrastinat",
            "lazy",
            "start studying",
            "cant start",
            "can't start",
            "distract",
            "phone",
            "focus",
            "concentrat"
        ],
        "HOW TO FOCUS / STOP PROCRASTINATING\n"
        "1. Start with just 5 minutes.\n"
        "2. Keep your phone away.\n"
        "3. Use Pomodoro: 25 min study, 5 min break.\n"
        "4. Write 3 tasks for today.\n"
        "5. Study at the same time and place daily."
    ),
    (
        ["revise", "revision", "memori", "remember", "memory", "forget"],
        "REVISION AND MEMORY TIPS\n"
        "1. Active recall.\n"
        "2. Spaced repetition.\n"
        "3. Teach the topic to someone.\n"
        "4. Use mnemonics and flashcards.\n"
        "5. Practice past papers."
    ),
    (
        ["exam", "test", "before exam", "last minute"],
        "EXAM PREPARATION\n"
        "1. Make a topic checklist.\n"
        "2. Solve past papers under timed conditions.\n"
        "3. Revise weak topics first.\n"
        "4. Sleep properly.\n"
        "5. Keep time to check answers."
    ),
    (
        ["note", "notes"],
        "NOTE-TAKING\n"
        "- Use headings and bullet points.\n"
        "- Write in your own words.\n"
        "- Add diagrams and examples.\n"
        "- Rewrite notes as questions."
    ),
]


FORMULAS = {
    "quadratic":
        "Quadratic formula: x = (-b +/- sqrt(b^2 - 4ac)) / (2a)",

    "pythagoras":
        "Pythagoras theorem: a^2 + b^2 = c^2",

    "circle":
        "Area of circle = pi x r^2. Circumference = 2 x pi x r",

    "triangle":
        "Area of triangle = 1/2 x base x height",

    "speed":
        "Speed = distance / time",

    "newton":
        "Newton's laws include F = m x a",

    "force":
        "Force: F = m x a",

    "motion":
        "Equations of motion: v = u + at, s = ut + 1/2 at^2, v^2 = u^2 + 2as",

    "ohm":
        "Ohm's law: V = I x R",

    "kinetic":
        "Kinetic energy = 1/2 m v^2",

    "potential":
        "Potential energy = m g h",

    "density":
        "Density = mass / volume",

    "mole":
        "Moles = mass / molar mass",

    "ph":
        "pH = -log10[H+]",

    "photosynthesis":
        "6CO2 + 6H2O + light energy -> C6H12O6 + 6O2",

    "percentage":
        "Percentage = (part / whole) x 100",

    "average":
        "Average = sum of values / number of values",
}


def find_formula(question):
    for key, formula in FORMULAS.items():
        if re.search(rf"\b{re.escape(key)}\b", question):
            return formula

    return None


def answer(question):
    q = question.lower().strip().rstrip("?.!")

    if re.search(r"\b(plan|timetable|schedule)\b", q):
        return make_plan(q)

    if re.search(r"\b(formula|equation|law|laws|theorem)\b", q):
        formula = find_formula(q)

        if formula:
            return formula

    best = None
    best_hits = 0

    for keys, text in TOPICS:
        hits = sum(1 for key in keys if key in q)

        if hits > best_hits:
            best = text
            best_hits = hits

    if best:
        return best

    formula = find_formula(q)

    if formula:
        return formula

    if re.search(r"\b(hi|hello|hey)\b", q):
        return (
            "Hi! I'm your study assistant. "
            "Ask me to plan a study session or ask for study tips."
        )

    if re.search(r"\b(thanks|thank you)\b", q):
        return "You're welcome! Good luck with your studies."

    return (
        "Sorry, I don't know that one yet. "
        "Try 'plan a 2 day timetable for maths and physics'."
    )
