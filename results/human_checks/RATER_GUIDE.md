# Human rating guide

There are three sheets in this folder. Fill in only the last column of each, on your own, without discussing your answers with anyone and without using any AI tool. These sheets are how the automatic labels get checked against people.

Open each CSV in Excel. If you see strange characters, use Data → From Text/CSV and choose UTF-8. When you're done, save it as CSV under the same file name. Do not reorder, add or delete rows or columns.

## 1. Gold sheets: `gold_sheet_rater_a.csv` and `gold_sheet_rater_b.csv`

There are two raters, one sheet each. Both sheets hold the same 199 pairs, in different orders.

Each row is one situation:

- A user sent the **new_request**.
- The **reference_answer** is what they actually got back.
- The cache holds an **earlier_request** and the **cached_answer** that was given to it.

Question: if the gateway had returned the cached answer, unchanged, would that have been an acceptable reply to the new request?

Write `YES` or `NO` in `acceptable_YES_NO`.

**YES** means the cached answer does what the new request asks: the same task, the same material, the same specifics. Small wording differences are fine. It does not have to match the reference word for word. Use the reference to understand what the user really needed.

**NO** applies when any of these is true:

- **A different ask on the same text.** For example, "summarize this" vs "list the key points of this".
- **Different specifics.** For example: a different number of items, different numbers, names, code, error message, length, format, or language. "Give 20 more" answered with 10 is a NO.
- **The request depends on earlier conversation the cached answer doesn't reflect.** For example: "continue", "make it shorter", "translate above", "stay in character".
- **The cached answer is a refusal, an error, or cut off,** and the user would not have wanted that.

Long texts are cut with `[...]` in the middle. Judge from what is shown.

## 2. Act sheet: `act_sheet.csv` (one rater)

For each row, read the **previous_turn** (it may be empty) and the **current_turn**. Write one of these in `act`:

- `new_request`: a self-contained new task or question.
- `follow_up`: refines or changes the previous answer. For example: shorter, longer, add X, change the style, more examples.
- `continuation`: asks the assistant to keep going ("continue", "go on", "next part").
- `correction`: says the previous answer was wrong or didn't work, or asks for it to be fixed.
- `new_ask_same_material`: a different task on material given earlier (the same pasted text or code, with a new instruction).

## Time

The gold sheets take about 30–45 seconds per row, roughly 2 hours each. The act sheet takes about 10 seconds per row, roughly an hour.
