"""Interactive AI Travel Agent (prices in Indian rupees, INR).

Unlike a one-shot form, this is a conversation: you can ask for a plan,
then keep talking to refine it - change the budget, add days, swap
activities, ask questions - across multiple turns.

Two modes, chosen automatically:

  1. AI mode      - if `anthropic` is installed AND ANTHROPIC_API_KEY is
                    set, you get a genuinely free-form chat with Claude,
                    which remembers the whole conversation.
  2. Offline mode - otherwise (or if an AI request ever fails), a
                    command-driven fallback keeps things interactive
                    without needing an API key. Type 'help' once inside
                    it to see the command list.

Setup for AI mode:
    pip install anthropic
    export ANTHROPIC_API_KEY="sk-ant-..."

Run:
    python3 travel_agent.py
"""

from __future__ import annotations

import json
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


def inr(amount: float) -> str:
    """Format a number as rupees with Indian digit grouping (e.g. ₹1,23,456)."""
    n = int(round(amount))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        s = f"{head},{tail}"
    return f"{'-' if n < 0 else ''}₹{s}"


def ask(prompt: str) -> str:
    """Optional field: blank is a valid answer (used for interests/month)."""
    return input(f"{prompt}: ").strip()


def ask_with_default(prompt: str, default: str) -> str:
    """Used only for things like file names, where a shown default is genuinely convenient."""
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def ask_required(prompt: str) -> str:
    """Keeps asking until the person actually types something - no default shown."""
    while True:
        value = input(f"{prompt}: ").strip()
        if value:
            return value
        print("  (please enter a value)")


def ask_int_required(prompt: str) -> int:
    """Keeps asking until a valid positive whole number is typed - no default shown."""
    while True:
        raw = input(f"{prompt}: ").strip()
        if raw.isdigit() and int(raw) > 0:
            return int(raw)
        print("  (please enter a whole number greater than 0)")


_BUDGET_ALIASES = {
    "budget": "budget", "cheap": "budget", "low": "budget", "economy": "budget",
    "mid": "mid-range", "mid-range": "mid-range", "midrange": "mid-range",
    "mid range": "mid-range", "medium": "mid-range", "med": "mid-range", "moderate": "mid-range",
    "luxury": "luxury", "high": "luxury", "high-end": "luxury", "premium": "luxury", "lux": "luxury",
}


def ask_budget_level() -> str:
    while True:
        raw = normalize(input("Budget level (budget / mid-range / luxury): "))
        level = _BUDGET_ALIASES.get(raw)
        if level:
            return level
        print("  (please enter one of: budget, mid-range, luxury)")


_SENTENCE_HINT_WORDS = {
    "trip", "plan", "day", "days", "budget", "traveler", "travelers", "people",
    "itinerary", "week", "weeks", "into", "for", "with",
}


def _looks_like_a_sentence(text: str) -> bool:
    words = text.lower().split()
    if len(words) > 6:
        return True
    return any(word.strip(",.") in _SENTENCE_HINT_WORDS for word in words)


def ask_destination() -> str:
    while True:
        value = ask_required("Destination (just a city or country name)")
        if _looks_like_a_sentence(value):
            print(
                "  That looks like a full sentence rather than a place name.\n"
                "  In offline mode I can't parse a whole request - please enter just\n"
                "  the city or country, e.g. 'Delhi'. (For free-form planning like\n"
                "  'plan a 5-day trip to Delhi...', set ANTHROPIC_API_KEY for AI mode.)"
            )
            continue
        return value


# ======================================================================
# AI mode - free-form multi-turn chat
# ======================================================================

AI_CHAT_SYSTEM_PROMPT = """You are a helpful, practical travel agent having an ongoing \
conversation with a traveler. Ask clarifying questions if you're missing key details \
(destination, trip length, budget, interests, number of travelers). Once you have \
enough to work with, propose a clear day-by-day itinerary with a few hotel options \
and a rough budget. When the traveler asks for changes (different budget, more/fewer \
days, different pace, swap an activity, etc.), revise your plan and restate only the \
parts that changed unless asked to restate everything. Keep responses well-organized \
and readable in plain text (use short headers and bullet points, no markdown tables). \
Never invent prices with false precision - give honest ranges. Quote all prices in \
Indian rupees (INR, ₹), converting from other currencies where needed."""


def _extract_text(response) -> str:
    return "\n".join(block.text for block in response.content if getattr(block, "type", "") == "text")


def run_ai_mode() -> None:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    messages: list[dict] = []

    print("\nTravel Agent (AI mode) - tell me about the trip you're thinking of.")
    print("Commands: 'save' to save the conversation, 'help' for tips, 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSafe travels!")
            return
        if not user_input:
            continue

        low = normalize(user_input)
        if low in {"exit", "quit", "bye"}:
            print("Safe travels!")
            return
        if low == "help":
            print(
                "\nJust talk naturally, e.g.:\n"
                "  'Plan a 5-day trip to Lisbon for 2 people, mid-range budget, into food and history'\n"
                "  'Make day 3 more relaxed'\n"
                "  'Swap the hotel for something cheaper'\n"
                "  'Add a day at the end'\n"
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
                max_tokens=1500,
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
        print(f"\nAgent: {reply_text}\n")


def _save_transcript(messages: list[dict]) -> None:
    if not messages:
        print("Nothing to save yet.")
        return
    filename = ask_with_default("File name", "trip_conversation.txt")
    with open(filename, "w", encoding="utf-8") as f:
        for m in messages:
            speaker = "You" if m["role"] == "user" else "Agent"
            f.write(f"{speaker}: {m['content']}\n\n")
    print(f"Saved conversation to {filename}")


# ======================================================================
# Offline mode - command-driven, no API key needed, always works
# ======================================================================

@dataclass
class TripRequest:
    destination: str
    days: int
    budget_level: str          # "budget", "mid-range", or "luxury"
    interests: list[str] = field(default_factory=list)
    travelers: int = 1
    travel_month: str = "unspecified"


# All amounts are in INR (rough conversion, about 85-88 INR per USD, rounded).
_BUDGET_DAILY_ACTIVITY_COST = {"budget": 2500, "mid-range": 6000, "luxury": 14000}
_BUDGET_HOTEL_NIGHTLY = {
    "budget": ("₹3,500-6,000", "₹6,000-8,500", "₹8,500-11,500"),
    "mid-range": ("₹9,000-13,000", "₹13,000-19,000", "₹19,000-26,000"),
    "luxury": ("₹26,000-40,000", "₹40,000-60,000", "₹60,000+"),
}

_ACTIVITY_TEMPLATES = {
    "food": [
        "Wander a local market and sample street food",
        "Take a food-focused walking tour of a historic district",
        "Book a table at a well-reviewed local restaurant",
        "Try a cooking class featuring regional dishes",
    ],
    "history": [
        "Visit the main historical museum or landmark",
        "Explore the old town / historic quarter on foot",
        "Tour a notable monument or heritage site",
    ],
    "walking": [
        "Take a self-guided walking tour of the city center",
        "Stroll through a scenic park or waterfront promenade",
    ],
    "hiking": [
        "Half-day hike on a nearby trail with good views",
        "Explore a nature reserve or scenic overlook",
    ],
    "nightlife": [
        "Evening out at a well-known local bar or live-music venue",
        "Sunset drinks at a rooftop or waterfront spot",
    ],
    "art": [
        "Visit a major art museum or gallery district",
        "Explore a neighborhood known for street art or local artisans",
    ],
    "shopping": [
        "Browse a well-known shopping street or local market",
        "Look for local crafts or souvenirs in an artisan district",
    ],
    "relaxation": [
        "Slow morning, café-hopping, no fixed plans",
        "Spa or wellness afternoon",
    ],
}
_DEFAULT_ACTIVITIES = [
    "Explore the city center and get oriented",
    "Visit a top-rated local landmark",
    "Free time to explore based on the day's mood",
]


def _price_midpoint(range_str: str) -> float:
    # Strip thousands separators first so "3,500" is read as 3500, not 3 and 500.
    numbers = [float(n) for n in re.findall(r"\d+", range_str.replace(",", ""))]
    return (sum(numbers) / len(numbers)) if numbers else 8000.0


def _activity_pool(interests: list[str]) -> list[str]:
    pool: list[str] = []
    for interest in interests:
        pool.extend(_ACTIVITY_TEMPLATES.get(interest.lower(), []))
    return pool or list(_DEFAULT_ACTIVITIES)


def build_day(trip: TripRequest, day_num: int, variant: int = 0) -> dict:
    pool = _activity_pool(trip.interests)
    start = ((day_num - 1) * 3 + variant * 3) % len(pool)
    picks = [pool[(start + i) % len(pool)] for i in range(3)]
    return {
        "day": day_num,
        "title": f"Day {day_num} in {trip.destination.title()}",
        "morning": picks[0],
        "afternoon": picks[1],
        "evening": picks[2],
        "estimated_cost": _BUDGET_DAILY_ACTIVITY_COST[trip.budget_level],
        "_variant": variant,
    }


def build_hotels(trip: TripRequest) -> list[dict]:
    low, mid, high = _BUDGET_HOTEL_NIGHTLY[trip.budget_level]
    dest = trip.destination.title()
    return [
        {"name": f"{dest} Central Stay", "area": "City center", "price_range_per_night": low,
         "why": "Walkable to major sights; good value. Generic placeholder - verify live availability."},
        {"name": f"{dest} Boutique Inn", "area": "Popular neighborhood", "price_range_per_night": mid,
         "why": "Comfortable mid-tier option often near restaurants and transit."},
        {"name": f"{dest} Signature Hotel", "area": "Prime district", "price_range_per_night": high,
         "why": "Higher-end option for extra comfort and amenities."},
    ]


def build_summary(trip: TripRequest) -> str:
    return (
        f"A {trip.days}-day {trip.budget_level} trip to {trip.destination.title()} "
        f"for {trip.travelers} traveler(s), focused on {', '.join(trip.interests) or 'general sightseeing'}. "
        "(Offline template - set ANTHROPIC_API_KEY for an AI-tailored version.)"
    )


def recompute_budget(trip: TripRequest, state: dict) -> None:
    daily_cost_sum = sum(day["estimated_cost"] for day in state["itinerary"])
    nights = trip.days
    mid_hotel_price = _price_midpoint(state["hotels"][1]["price_range_per_night"])
    accommodation_total = nights * mid_hotel_price
    food_total = daily_cost_sum * 0.4 * trip.travelers
    activities_total = daily_cost_sum * 0.6 * trip.travelers
    transport_total = trip.days * (800 if trip.budget_level == "budget" else 1600) * trip.travelers
    state["budget_estimate"] = {
        "accommodation": round(accommodation_total, 2),
        "food": round(food_total, 2),
        "activities": round(activities_total, 2),
        "local_transport": round(transport_total, 2),
        "total": round(accommodation_total + food_total + activities_total + transport_total, 2),
    }


def generate_offline(trip: TripRequest) -> dict:
    state = {
        "destination": trip.destination.title(),
        "trip_summary": build_summary(trip),
        "itinerary": [build_day(trip, d) for d in range(1, trip.days + 1)],
        "hotels": build_hotels(trip),
        "packing_tips": [
            "Check the weather for your travel month before packing",
            "Bring a portable charger and universal power adapter",
            "Carry a printed or offline copy of key bookings",
        ],
    }
    recompute_budget(trip, state)
    return state


def collect_trip_request() -> TripRequest:
    print("Let's set up your trip.\n")
    destination = ask_destination()
    days = ask_int_required("Number of days")
    travelers = ask_int_required("Number of travelers")
    budget_level = ask_budget_level()

    interests_raw = ask("Interests, comma-separated (e.g. food, history, hiking, nightlife) - optional")
    interests = [i.strip() for i in interests_raw.split(",") if i.strip()]
    travel_month = ask("Month of travel - optional")

    return TripRequest(
        destination=destination, days=days, budget_level=budget_level,
        interests=interests, travelers=travelers,
        travel_month=travel_month or "unspecified",
    )


# ---- Display helpers --------------------------------------------------

def format_itinerary_section(state: dict) -> str:
    lines = ["ITINERARY", "-" * 60]
    for day in state["itinerary"]:
        lines.append(f"\nDay {day['day']}")
        lines.append(f"  Morning:   {day['morning']}")
        lines.append(f"  Afternoon: {day['afternoon']}")
        lines.append(f"  Evening:   {day['evening']}")
        lines.append(f"  Est. daily spend (per person, excl. hotel): {inr(day['estimated_cost'])}")
    return "\n".join(lines)


def format_hotels_section(state: dict) -> str:
    lines = ["HOTEL SUGGESTIONS", "-" * 60]
    for hotel in state["hotels"]:
        lines.append(f"\n{hotel['name']} - {hotel['area']}")
        lines.append(f"  {hotel['price_range_per_night']} / night")
        lines.append(f"  {hotel['why']}")
    return "\n".join(lines)


def format_budget_section(state: dict) -> str:
    b = state["budget_estimate"]
    return (
        "ROUGH BUDGET (whole trip, INR)\n" + "-" * 60 +
        f"\n  Accommodation:   {inr(b['accommodation'])}"
        f"\n  Food:            {inr(b['food'])}"
        f"\n  Activities:      {inr(b['activities'])}"
        f"\n  Local transport: {inr(b['local_transport'])}"
        f"\n  TOTAL:           {inr(b['total'])}"
    )


def format_full(state: dict) -> str:
    line = "=" * 60
    parts = [
        f"{line}\nTRIP PLAN: {state['destination']}\n{line}",
        state["trip_summary"],
        format_itinerary_section(state),
        format_hotels_section(state),
        "PACKING TIPS\n" + "-" * 60 + "\n" + "\n".join(f"  - {t}" for t in state["packing_tips"]),
        format_budget_section(state),
        line,
    ]
    return "\n\n".join(parts)


def save_to_file(state: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"Saved full itinerary to {path}")


# ---- Command handling ---------------------------------------------------

OFFLINE_HELP = textwrap.dedent("""
    Commands you can use:
      show itinerary / show hotels / show budget / show everything
      add a day                       - append another day at the current pace
      remove a day                    - drop the last day
      regenerate day <n>               - swap that day's activities for alternatives
      change budget to <level>         - budget / mid-range / luxury
      add interest <topic>             - affects new or regenerated days
      remove interest <topic>
      save                              - save the plan to a JSON file
      help                              - show this again
      exit                              - quit
""").strip()


def handle_offline_command(message: str, trip: TripRequest, state: dict) -> Optional[str]:
    """Returns a response string, or None if the command wasn't recognized."""
    msg = normalize(message)

    if msg in {"show itinerary"}:
        return format_itinerary_section(state)
    if msg in {"show hotels"}:
        return format_hotels_section(state)
    if msg in {"show budget"}:
        return format_budget_section(state)
    if msg in {"show everything", "show all", "show plan", "show"}:
        return format_full(state)

    if re.match(r"^add (a |one )?day$", msg):
        trip.days += 1
        state["itinerary"].append(build_day(trip, trip.days))
        state["trip_summary"] = build_summary(trip)
        recompute_budget(trip, state)
        return f"Added Day {trip.days}.\n\n" + format_itinerary_section(state)

    if re.match(r"^(remove|delete) (a |one |the last )?day$", msg):
        if trip.days <= 1:
            return "You only have one day left - can't remove it."
        state["itinerary"].pop()
        trip.days -= 1
        state["trip_summary"] = build_summary(trip)
        recompute_budget(trip, state)
        return f"Removed the last day. Now {trip.days} day(s).\n\n" + format_itinerary_section(state)

    m = re.match(r"^regenerate day (\d+)$", msg)
    if m:
        n = int(m.group(1))
        if not (1 <= n <= trip.days):
            return f"There's no Day {n} in the current plan (1-{trip.days})."
        variant = state["itinerary"][n - 1].get("_variant", 0) + 1
        state["itinerary"][n - 1] = build_day(trip, n, variant=variant)
        return f"Regenerated Day {n}.\n\n" + format_itinerary_section(state)

    m = re.match(r"^(change |set )?budget( to| as)? (budget|mid-range|midrange|mid range|luxury)$", msg)
    if m:
        level = m.group(3).replace("midrange", "mid-range").replace("mid range", "mid-range")
        trip.budget_level = level
        for day in state["itinerary"]:
            day["estimated_cost"] = _BUDGET_DAILY_ACTIVITY_COST[level]
        state["hotels"] = build_hotels(trip)
        state["trip_summary"] = build_summary(trip)
        recompute_budget(trip, state)
        return f"Budget level set to {level}.\n\n" + format_hotels_section(state) + "\n\n" + format_budget_section(state)

    m = re.match(r"^add interest[:\s]+(.+)$", msg)
    if m:
        topic = m.group(1).strip()
        if topic and topic not in trip.interests:
            trip.interests.append(topic)
        state["trip_summary"] = build_summary(trip)
        return f"Added '{topic}' to interests. Use 'regenerate day <n>' or 'add a day' to see it reflected."

    m = re.match(r"^remove interest[:\s]+(.+)$", msg)
    if m:
        topic = m.group(1).strip()
        if topic in trip.interests:
            trip.interests.remove(topic)
            state["trip_summary"] = build_summary(trip)
            return f"Removed '{topic}' from interests."
        return f"'{topic}' wasn't in your interests list."

    if msg == "help":
        return OFFLINE_HELP

    return None


def run_offline_mode() -> None:
    if not _ANTHROPIC_AVAILABLE:
        print("\n(`anthropic` package not installed - running in offline mode.)")
    elif not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n(No ANTHROPIC_API_KEY set - running in offline mode.)")

    trip = collect_trip_request()
    state = generate_offline(trip)
    print()
    print(format_full(state))
    print("\nYou can now chat to adjust the plan. Type 'help' to see commands, 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSafe travels!")
            return
        if not user_input:
            continue

        low = normalize(user_input)
        if low in {"exit", "quit", "bye"}:
            print("Safe travels!")
            return
        if low == "save":
            default_name = f"{trip.destination.lower().replace(' ', '_')}_itinerary.json"
            filename = ask_with_default("File name", default_name)
            save_to_file(state, filename)
            continue

        response = handle_offline_command(user_input, trip, state)
        if response is None:
            response = "I didn't recognize that command. Type 'help' to see what I can do."
        print(f"\nAgent:\n{response}\n")


# ======================================================================
# Main
# ======================================================================

def main() -> None:
    print("=" * 60)
    print("INTERACTIVE TRAVEL AGENT")
    print("=" * 60)

    use_ai = _ANTHROPIC_AVAILABLE and bool(os.environ.get("ANTHROPIC_API_KEY"))
    if use_ai:
        run_ai_mode()
    else:
        run_offline_mode()


if __name__ == "__main__":
    main()