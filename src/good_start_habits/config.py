"""Globals are defined here"""

from random import randint

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


ROTATION_INTERVAL = randint(5, 15)  # (1800,7200)
DWELL_TIME = randint(5, 15)  # (1800,7200)

# Monthly budget limits per personal category (£)
BUDGET_LIMITS: dict[str, float] = {
    "Food & Groceries": 300.0,
    "Eating Out": 150.0,
    "Travel & Transport": 100.0,
    "Subscriptions": 80.0,
    "Shopping": 150.0,
    "Entertainment": 60.0,
    "Health & Beauty": 50.0,
    "Bills & Utilities": 200.0,
    "Other": 100.0,
}

# Maps TrueLayer classification strings to personal categories.
# Keys with a "|" are matched on "top|sub"; plain keys on top-level only.
CATEGORY_MAP: dict[str, str] = {
    "Food|Groceries": "Food & Groceries",
    "Food|Coffee Shops": "Eating Out",
    "Food|Takeaway": "Eating Out",
    "Food|Restaurants": "Eating Out",
    "Food": "Eating Out",
    "Groceries": "Food & Groceries",
    "Restaurants": "Eating Out",
    "Coffee Shops": "Eating Out",
    "Takeaway": "Eating Out",
    "Transport": "Travel & Transport",
    "Travel": "Travel & Transport",
    "Taxi": "Travel & Transport",
    "Subscription": "Subscriptions",
    "Subscriptions": "Subscriptions",
    "Entertainment": "Entertainment",
    "Shopping": "Shopping",
    "Home & Garden": "Shopping",
    "Healthcare": "Health & Beauty",
    "Health & Beauty": "Health & Beauty",
    "Personal Care": "Health & Beauty",
    "Sports & Fitness": "Health & Beauty",
    "Bills": "Bills & Utilities",
    "Utilities": "Bills & Utilities",
    "Bill Payments": "Bills & Utilities",
    "Hobbies": "Entertainment",
}
