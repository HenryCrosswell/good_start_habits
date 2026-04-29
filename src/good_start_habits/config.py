"""Globals are defined here"""

from random import randint
from typing import Any

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


ROTATION_INTERVAL = randint(1800, 7200)  # (5, 15)
DWELL_TIME = randint(300, 600)  # (5, 15)

# Which categories belong to which provider (drives per-tab budget limits).
# Transport is split: trains on Amex, parking on Nationwide.
PROVIDER_BUDGET_LIMITS: dict[str, dict[str, float]] = {
    "nationwide": {  # these categories only, anything else wouldbe an error
        "Rent": 1475.0,
        "Bills & Utilities": 242.33,
        "Transport": 100.0,  # parking direct debit
        "Subscriptions": 82.0,
    },
    "amex": {  # these categories only, anything else wouldbe an error
        "Groceries": 160.0,
        "Transport": 330.0,  # trains season ticket / ad-hoc travel
    },
    "monzo": {  # these categories only, anything else wouldbe an error
        "Food & Coffee": 130.0,
        "Eating Out & Social": 170.0,
    },
}

""" Savings currently
LISA and ISA you can find from AJBELL contributions currently there.
    ISA = 7,119.36 - adventurous account (interest rates vary)
    LISA = 24,434.88 - balanced account (1k extra if 4k is deposited)

Nationwide savings
    nationwide = 1000 - 6.5% currently

Bonds
    bonds = 1025 - return is gambling

ATOM should NOT BE INCLUDED IN SAVINGS, it is easy accessible and not used for long-term savings just
emergency, holiday, car etc.etc.
"""

# Monthly budget limits per personal category (£)
BUDGET_LIMITS: dict[str, float] = {
    "Groceries": 160.0,  # big food shop
    "Food & Coffee": 130.0,  # misc food, coffees, snacks
    "Eating Out & Social": 170.0,  # restaurants, bars, nights out
    "Rent": 1475.0,  # full outgoing; GF contribution tracked via extra_income
    "Bills & Utilities": 242.33,  # full outgoing; GF contribution tracked via extra_income
    "Transport": 430.0,  # trains (330) + parking (100)
    "Petrol": 60.0,  # £60, 01/04/07/10 — sinking fund - resets at start of these months
    "Subscriptions": 82.0,  # gym (50) + phone (10) + claude (18) + tesco (4)
    "Lastpass": 38,  # £38, 01 — sinking fund
    "Proton": 64.95,  # £64.95, 01 — sinking fund
    "Haircut": 45,  # £45, 02/04/06/08/10/12 — sinking fund
    "Skin & Haircare": 20.0,  # £20, 01/05/09 — sinking fund
    "Gigs": 30.0,  # £30, 01/04/07/10 sinking fund
    "Steam Games": 15.0,  # £15, 01/04/07/10 — sinking fund
    "Clothing": 60.0,  # £60, 01/07 — sinking fund
    "Gifts": 37.50,  # every month - sinking fund
    "House Products": 60.0,  # £60, 01/05/09 — sinking fund
    "Other": 20.0,  # random misc
}


# Maps TrueLayer classification strings to personal categories.
# Keys with a "|" are matched on "top|sub"; plain keys on top-level only.
CATEGORY_MAP: dict[str, Any] = {
    # Groceries
    "Food|Groceries": "Groceries",
    "Groceries": "Groceries",
    # Misc food and coffee
    "Food|Coffee Shops": "Food & Coffee",
    "Food|Bakeries": "Food & Coffee",
    "Coffee Shops": "Food & Coffee",
    "Food": "Food & Coffee",
    # Eating out
    "Food|Restaurants": "Eating Out & Social",
    "Food|Takeaway": "Eating Out & Social",
    "Food|Dining": "Eating Out & Social",
    "Food|Bars": "Eating Out & Social",
    "Restaurants": "Eating Out & Social",
    "Takeaway": "Eating Out & Social",
    "Bars": "Eating Out & Social",
    # Entertainment
    "Entertainment": "Eating Out & Social",
    "Hobbies": "Eating Out & Social",
    # Rent / housing
    "Housing": "Rent",
    "Rent": "Rent",
    # Bills
    "Bills": "Bills & Utilities",
    "Utilities": "Bills & Utilities",
    "Bill Payments": "Bills & Utilities",
    "Home & Garden": "Bills & Utilities",
    # Transport
    "Transport": "Transport",
    "Travel": "Transport",
    "Taxi": "Transport",
    "Parking": "Transport",
    "Fuel": "Petrol",
    "Public Transport": "Transport",
    # Subscriptions
    "Subscription": "Subscriptions",
    "Subscriptions": "Subscriptions",
    "Sports & Fitness": "Subscriptions",
    # Personal care / skin
    "Healthcare": "Skin & Haircare",
    "Health & Beauty": "Skin & Haircare",
    "Personal Care": "Skin & Haircare",
    # Other (shopping, clothing, gifts, etc.)
    "Shopping": "Other",
    "Clothing": "Other",
    # Transfers / savings movements — excluded from spending totals
    "Transfer": None,
    "Transfers": None,
    "Internal Transfer": None,
    "Savings": None,
    "Income": None,
}

# Description-based fallback patterns (case-insensitive substring match, first wins).
# None means exclude from spending entirely.
BASE_INCOME: float = 2440.0
DEFAULT_EXTRA_INCOME: float = 880.0

CATEGORY_GROUPS: dict[str, list[str]] = {
    "Fixed": ["Rent", "Bills & Utilities", "Transport", "Subscriptions"],
    "Essentials": ["Groceries", "Food & Coffee"],
    "Discretionary": [
        "Eating Out & Social",
        "Entertainment",
        "Skin & Haircare",
        "Other",
    ],
    "Sinking Fund": [
        "Haircut",
        "Gigs",
        "Steam Games",
        "Clothing",
        "Gifts",
        "House Products",
        "Petrol",
        "Lastpass",
        "Proton",
    ],
}

SINKING_FUND_RESETS: dict[str, list[int]] = {
    "Petrol": [1, 4, 7, 10],
    "Lastpass": [1],
    "Proton": [1],
    "Haircut": [2, 4, 6, 8, 10, 12],
    "Skin & Haircare": [1, 5, 9],
    "Gigs": [1, 4, 7, 10],
    "Steam Games": [1, 4, 7, 10],
    "Clothing": [1, 7],
    "Gifts": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    "House Products": [1, 5, 9],
}

SAVINGS_ACCOUNTS: list[dict] = [
    {
        "name": "LISA",
        "patterns": ["lifetime isa", "moneybox", "lisa"],
        "colour": "#FF1493",
        "annual_bonus_rate": 0.25,  # 25% government bonus
        "annual_bonus_cap": 4000.0,  # capped at £4k contributions/year
        "default_balance": 24434.88,
    },
    {
        "name": "AJ Bell",
        "patterns": ["aj bell"],
        "colour": "#9B30FF",
        "annual_return_rate": 0.07,  # estimated 7% blended return
        "default_balance": 7119.36,
    },
    {
        "name": "Premium Bonds",
        "patterns": ["ns&i", "premium bonds"],
        "colour": "#FFD700",
        "annual_prize_rate": 0.044,  # 4.4% average annual prize rate
        "default_balance": 1025.0,
    },
    {
        "name": "Atom",
        "patterns": ["atom"],
        "colour": "#FF6B00",
        "annual_return_rate": 0.05,  # 5% fixed-rate savings
        "default_balance": 0.0,
    },
    {
        "name": "Nationwide",
        "patterns": ["nationwide sav", "flex saver"],
        "colour": "#00B4D8",
        "annual_return_rate": 0.045,  # ~4.5% easy-access rate
        "default_balance": 1000.0,
    },
]

SAVINGS_PATTERNS: list[str] = [
    p for acc in SAVINGS_ACCOUNTS for p in acc["patterns"]
] + ["bonds"]

DESCRIPTION_PATTERNS: list[tuple[str, str | None]] = [
    # ── Exclude: internal transfers, savings movements ───────────────────────
    ("left-over monthly", None),  # Monzo internal rounding
    ("transfer to", None),
    ("transfer from", None),
    ("payment to henry crosswell", None),
    ("payment received", None),  # Amex credit-card payment confirmation
    ("american express", None),  # Nationwide paying off Amex balance
    ("ns&i", None),
    ("aj bell", None),
    ("premium bonds", None),
    ("atom", None),  # savings transfers to Atom
    ("moneybox", None),  # Moneybox LISA/ISA
    ("lifetime isa", None),  # generic LISA transfers
    ("flex saver", None),  # Nationwide Flex Saver
    ("nationwide sav", None),  # Nationwide savings account
    # ── Rent ─────────────────────────────────────────────────────────────────
    ("ashton", "Rent"),
    # ── User-confirmed Nationwide payees ─────────────────────────────────────
    ("amrit.kaur", "Bills & Utilities"),  # GF council tax repayment (dominant) + misc
    ("stalbans.gov", "Transport"),  # St Albans parking permit
    ("voxi", "Subscriptions"),  # phone SIM
    ("everyoneactive", "Subscriptions"),  # gym membership
    ("studio 10", "Haircut"),  # hair salon
    ("zizzi", "Eating Out & Social"),
    ("evan cryer-jenkins", "Other"),  # misc payment to friend
    ("malt miller", "Entertainment"),  # homebrewing supplies
    ("o2 shepherd", "Gigs"),  # gig venue
    ("o2 academy", "Gigs"),  # gig venue
    ("proto artisan", "Food & Coffee"),  # artisan bakery/cafe
    ("grind", "Food & Coffee"),  # Grind coffee chain
    ("arriva", "Transport"),  # bus operator
    ("fealla", "Clothing"),  # local clothing merchant
    ("arket", "Clothing"),  # clothing (H&M group)
    ("johnlewis", "Other"),
    ("john lewis", "Other"),
    ("wilko", "House Products"),
    ("itsu", "Eating Out & Social"),
    ("hawk", "Eating Out & Social"),  # Hawks Nest pub
    ("beehive", "Eating Out & Social"),
    ("great northern", "Eating Out & Social"),
    ("white lion", "Eating Out & Social"),
    ("bunches", "Gifts"),  # flowers / gifts
    ("holland & barrett", "Skin & Haircare"),
    ("jade pharmacy", "Skin & Haircare"),
    ("dropout", "Subscriptions"),
    # ── Bills & Utilities (direct debits not matched above) ──────────────────
    ("dvla", "Transport"),  # car tax direct debit
    ("direct debit", "Bills & Utilities"),
    ("standing order", "Bills & Utilities"),
    # ── Food & Coffee (small supermarket / convenience / coffee) ─────────────
    ("tesco", "Food & Coffee"),
    ("sainsbury", "Food & Coffee"),
    ("m&s", "Food & Coffee"),
    ("marks & spencer", "Food & Coffee"),
    ("marks&spencer", "Food & Coffee"),  # alternate ampersand format
    ("iceland", "Food & Coffee"),
    ("waitrose", "Food & Coffee"),
    ("aldi", "Food & Coffee"),
    ("lidl", "Food & Coffee"),
    ("asda", "Food & Coffee"),
    ("morrisons", "Food & Coffee"),
    ("greggs", "Food & Coffee"),
    ("costa", "Food & Coffee"),
    ("starbucks", "Food & Coffee"),
    ("caffe nero", "Food & Coffee"),
    ("pret", "Food & Coffee"),
    ("nkora", "Food & Coffee"),
    ("darlish", "Food & Coffee"),
    # ── Eating Out & Social ───────────────────────────────────────────────────
    ("pizza", "Eating Out & Social"),
    ("franco manca", "Eating Out & Social"),
    ("bierkeller", "Eating Out & Social"),
    ("bier keller", "Eating Out & Social"),  # spaced variant
    ("greene king", "Eating Out & Social"),
    ("blacksmith", "Eating Out & Social"),
    ("the gallery", "Eating Out & Social"),
    ("red lion", "Eating Out & Social"),
    ("broad street tavern", "Eating Out & Social"),
    ("carpenters arms", "Eating Out & Social"),
    ("the odyssey", "Eating Out & Social"),
    ("simmons", "Eating Out & Social"),
    ("wokingham saviour", "Eating Out & Social"),
    ("nandos", "Eating Out & Social"),
    ("wagamama", "Eating Out & Social"),
    ("wetherspoon", "Eating Out & Social"),
    ("spoons", "Eating Out & Social"),
    ("restaurant", "Eating Out & Social"),
    # ── Transport ─────────────────────────────────────────────────────────────
    ("trainline", "Transport"),
    ("tfl", "Transport"),
    ("national rail", "Transport"),
    ("uber", "Transport"),
    # ── Petrol ────────────────────────────────────────────────────────────────
    ("shell", "Petrol"),
    ("bp", "Petrol"),
    ("esso", "Petrol"),
    ("texaco", "Petrol"),
    ("moto", "Petrol"),  # motorway services
    ("euro garages", "Petrol"),
    # ── Skin & Haircare ───────────────────────────────────────────────────────
    ("benefit cosmetics", "Skin & Haircare"),
    ("benefit", "Skin & Haircare"),
    ("superdrug", "Skin & Haircare"),
    ("boots", "Skin & Haircare"),
    ("barber", "Haircut"),
    ("hairdress", "Haircut"),
    # ── Gigs ──────────────────────────────────────────────────────────────────
    ("lw theatre", "Gigs"),
    ("ticketmaster", "Gigs"),
    # ── Entertainment ─────────────────────────────────────────────────────────
    ("waterstones", "Entertainment"),
    ("odeon", "Entertainment"),
    ("vue cinema", "Entertainment"),
    # ── Subscriptions ─────────────────────────────────────────────────────────
    ("spotify", "Subscriptions"),
    ("netflix", "Subscriptions"),
    ("claude", "Subscriptions"),
    ("anthropic", "Subscriptions"),
    ("lastpass", "Lastpass"),
    ("proton", "Proton"),
    # ── Steam Games ───────────────────────────────────────────────────────────
    ("steam", "Steam Games"),
    # ── Clothing ──────────────────────────────────────────────────────────────
    ("zara", "Clothing"),
    ("primark", "Clothing"),
    ("h&m", "Clothing"),
    # ── House Products ────────────────────────────────────────────────────────
    ("robert dyas", "House Products"),
    # ── Other ─────────────────────────────────────────────────────────────────
    ("amazon", "Other"),
    ("paypal", "Other"),
    ("garmin", "Other"),
]
