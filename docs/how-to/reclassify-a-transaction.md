# How to reclassify a transaction

There are two ways to fix a transaction landing in the wrong category.

---

## Option 1: Sort tab (batch workflow)

Switch to the **Sort** view (`?view=sort`) to see all uncategorised transactions for the current month — ones that haven't been assigned an override yet.

Each row has a category dropdown and a **SAVE RULE** button. Selecting a category and clicking SAVE RULE:

- Stores the override in the `category_overrides` table immediately (no page reload).
- Removes the row from the sort list.
- Every future transaction with the same description will use that category.

To exclude a transaction from all spend totals, select **Transfer** and save. It disappears from every budget chart.

---

## Option 2: Edit overlay (on the chart view)

On the month view, click the **EDIT** button below any category chart to open an overlay listing every transaction in that category. Click a transaction row to bring up a dropdown and a **SAVE** button.

Saving moves the transaction to the new category immediately without a page reload. The overlay updates in place — the transaction leaves the old category list and appears in the new one.

---

## Option 3: Add a description pattern to config (permanent)

For merchants that recur and are consistently miscategorised, add a pattern to `DESCRIPTION_PATTERNS` in `config.py`:

```python
DESCRIPTION_PATTERNS = [
    ...
    ("merchant substring", "Correct Category"),
]
```

The match is case-insensitive and substring-based. First match wins, so place more specific patterns above generic ones like `("amazon", "Other")`.

Restart the app after changing `config.py`.

Config patterns take priority over inline overrides set through the UI.

---

## Marking a transaction as a transfer (exclude from totals)

If a transaction represents money you already accounted for (e.g. a credit card payment, a savings transfer), assign it the **Transfer** category in either the Sort tab or the edit overlay. The transaction will be excluded from all spend totals, exactly like internal bank transfers detected automatically.

---

## Moving a transaction back to the sort queue

The **UNSORT** button appears on each transaction row in the month view. Clicking it reclassifies the transaction as **Other** and removes it from the current view. It will then appear in the Sort tab, where you can assign it a correct category or mark it as Transfer.

This replaces the old SF (Sinking Fund) button.
