# How to reclassify a transaction

There are two ways to fix a transaction landing in the wrong category.

---

## Option 1: Inline reclassify (one-off, persisted)

On the budget page, find the transaction in the transaction list. Click the category label or the edit icon next to the transaction. Select the correct category from the dropdown and confirm.

This stores the reclassification in the `category_overrides` SQLite table, keyed on the transaction's description (lowercased). Every future transaction with the same description will use the overridden category.

This is the right choice for:
- A merchant you don't want to add permanently to `config.py`
- A one-off large purchase that landed in the wrong bucket

---

## Option 2: Add a description pattern to config (permanent)

For merchants that recur and are consistently miscategorised, add a pattern to `DESCRIPTION_PATTERNS` in `config.py`:

```python
DESCRIPTION_PATTERNS = [
    ...
    ("merchant substring", "Correct Category"),
]
```

The match is case-insensitive and substring-based. First match wins, so place more specific patterns above generic ones like `("amazon", "Other")`.

Restart the app after changing `config.py`.

This overrides inline reclassifications — the config pattern takes priority.

---

## Marking a transaction as a transfer (exclude from totals)

If a transaction represents money you already accounted for (e.g. a large purchase funded by a prior Atom transfer), mark it as a transfer so it doesn't double-count as spending.

Use the inline reclassify, but select **Transfer** from the category dropdown. The transaction will be excluded from all spend totals, exactly like internal bank transfers.

---

## Sinking fund override

If a transaction should count toward a sinking fund period rather than the current month's discretionary spend, use the sinking fund panel on the budget page. This stores the description in `sinking_fund_overrides` and the transaction is excluded from regular category totals.
