"""Globals are defined here"""

HABITS = [
    "SPF applied",
    "Vitamins & Omega-3",
    "Log meal",
    "Piano practice",
    "Journal entry",
    "Neuroscience notes",
    "Check to-do List",
    "Track workout",
    "Track run",
]

HABIT_ACTIVE_DAYS: dict[str, list[str]] = {
    "SPF applied": [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ],
    "Vitamins & Omega-3": [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ],
    "Log meal": [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ],
    "Piano practice": [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ],
    "Journal entry": [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ],
    "Neuroscience notes": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "Check To-Do List": [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ],
    "Track workout": ["Monday", "Wednesday", "Friday"],
    "Track run": ["Tuesday", "Thursday", "Saturday"],
}

ACTIVE_TIMES = {
    "Monday": ("06:00:00", "21:00:00"),
    "Tuesday": ("06:00:00", "21:00:00"),
    "Wednesday": ("06:00:00", "21:00:00"),
    "Thursday": ("06:00:00", "21:00:00"),
    "Friday": ("06:00:00", "21:00:00"),
    "Saturday": ("08:00:00", "21:00:00"),
    "Sunday": ("08:00:00", "21:00:00"),
}
