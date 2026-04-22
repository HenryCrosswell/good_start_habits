"""Globals are defined here"""

HABITS = [
    "SPF applied",
    "Vitamins & Omega-3",
    "Log meal",
    "Piano practice",
    "Journal entry",
    "Neuroscience notes",
    "Check to-do book",
    "Workout logged",
    "Run logged",
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
    "Log Meal": [
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
    "Journal Entry": [
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
    "Track Workout": ["Monday", "Wednesday", "Friday"],
    "Track Run": ["Tuesday", "Thursday", "Saturday"],
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
