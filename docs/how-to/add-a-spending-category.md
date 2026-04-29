# How to add a spending category

---

## Add the category limit

In `config.py`, add an entry to `BUDGET_LIMITS`:

```python
BUDGET_LIMITS = {
    ...
    "New Category": 50.0,   # monthly limit in pounds
}
```

Also add it to the appropriate group in `CATEGORY_GROUPS` so it appears in the right section of the budget page:

```python
CATEGORY_GROUPS = {
    "Fixed": [...],
    "Essentials": [...],
    "Discretionary": [..., "New Category"],
    "Sinking Fund": [...],
}
```

---

## Map TrueLayer classifications to the category

TrueLayer returns a `transaction_classification` list (e.g. `["Food", "Groceries"]`). Add entries to `CATEGORY_MAP` in `config.py`:

```python
CATEGORY_MAP = {
    ...
    "Food|Groceries": "New Category",   # matches top-level "Food", sub-level "Groceries"
    "Groceries": "New Category",        # matches top-level only
}
```

Keys with `|` match both the top-level and sub-level classification. Keys without `|` match the top-level only.

---

## Add merchant patterns as a fallback

For transactions TrueLayer can't classify (or classifies too broadly), add entries to `DESCRIPTION_PATTERNS`:

```python
DESCRIPTION_PATTERNS = [
    ...
    ("merchant name", "New Category"),   # case-insensitive substring match
]
```

First match wins, so order matters. Put more specific patterns above generic ones.

---

## Assign to a provider (optional)

If the category is always charged to a specific card, add it to `PROVIDER_BUDGET_LIMITS` so the per-provider view shows the correct limit:

```python
PROVIDER_BUDGET_LIMITS = {
    "monzo": {
        ...
        "New Category": 50.0,
    },
    ...
}
```

Categories not in a provider's limits will show as WRONG CARD on that provider's view.

---

## Keeping BUDGET_LIMITS in sync with PROVIDER_BUDGET_LIMITS

The total in `BUDGET_LIMITS` for a category should equal the sum of that category across all providers. If you change a provider limit, update `BUDGET_LIMITS` too. See [Reference: Config](../reference/config.md#budget_limits-vs-provider_budget_limits) for more on this.

---

## Restart the app

`config.py` is loaded at import time. Restart the app after any change.
