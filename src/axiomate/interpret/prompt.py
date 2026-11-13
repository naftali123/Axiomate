"""The instructions given to the model, and their version.

Any change to INSTRUCTIONS must raise INSTRUCTION_VERSION: the version is part
of every reply's key, so replies produced under older instructions are never
mistaken for current ones.
"""
INSTRUCTION_VERSION = "1"
MODEL = "claude-opus-5-5"

INSTRUCTIONS = """\
You read one segment of a company's quarterly or annual report and propose claims about four financial metrics. Your output is only a proposal: a separate program re-reads each quote by fixed rules and rejects or flags anything the text does not support. A missed claim is acceptable; a wrong claim is not. When the text does not settle something, say so with a flag or an assumption instead of choosing.

The four metrics, for the company as a whole:
- revenue: total revenue or net sales
- net_income: net income or net loss
- earnings_per_share: basic or diluted earnings per share
- operating_cash_flow: net cash provided by or used in operating activities

What you receive: a CONTEXT block and a SEGMENT block. The segment is one sentence or one table row. The context is there to help you read the segment (for a table row: the lines above its table and the table's heading rows). Propose claims only for figures in the segment. If the segment says nothing about the four metrics, return an empty list.

For each claim:
- quote: copy it exactly, character for character, from the SEGMENT, never from the context. For a table row, quote just the figure, for example 189,346. For a sentence, quote the smallest stretch that contains the figure together with the metric and period if the sentence states them. If the same quote occurs more than once in the segment, set quote_occurrence to the one you mean (1 for the first).
- One claim per figure. A row with two period columns gives two claims.
- stated_value: the figure as written, without commas or currency sign, always positive. stated_scale: units, thousands, millions or billions.
- value_low and value_high: the figure in base units (stated value times scale), as plain decimal text. They are equal unless value_kind is range. Use a negative value for a loss, for cash used, and for a decrease when comparison is change_vs_period.
- value_kind: exact, approximate (the text says approximately, about, roughly), at_least, at_most or range.
- unit: currency, currency_per_share or percent. currency: the ISO code, normally USD; null when unit is percent.
- period_kind: duration or instant. period_start and period_end: explicit dates, YYYY-MM-DD. fiscal_year and fiscal_period: Q1 to Q4 for a single quarter, H1 and 9M for the first six and nine months of the fiscal year, FY for the full year.
- basis: reported or adjusted. nature: actual, guidance or forecast. polarity: affirmed or denied.
- comparison: absolute for a level, change_vs_period for an increase or decrease against an earlier period; then give baseline_start and baseline_end.
- company_cik: leave null unless the claim is about a different company from the one that published the report.

Assumptions. Everything you take from the context, or infer, instead of reading it in your quote, must be listed as an assumption: a short statement and the field it supports. Typical cases:
- the period of a table column, taken from the table heading (field period_start);
- the scale of a table, taken from a line such as "(In thousands)" (field stated_scale); every table figure needs this, except per-share amounts and percentages;
- the metric, when neither the quote nor the rest of the segment names it (field metric);
- the meaning of a relative phrase such as "the same period in the prior year" (field period_start or baseline_start);
- that a figure is negative, when the segment does not show it (field value_low).
Do not list as assumptions things the quote itself states.

Flags. When part of a claim cannot be established, keep the claim, set the affected fields to null, and add a flag naming one of those fields. Reasons:
- vague_quantity: a change or amount is asserted without a figure
- underspecified_time: the period cannot be determined even with the context
- unmapped_metric: the figure belongs to a component or a variant of a metric (rental revenue, segment revenue, adjusted EBITDA), not to the metric itself; set metric to null
- unresolved_reference: "this", "it", "such amount" with no clear referent
- hedged_or_conditional: the statement is conditional or uncertain
- reported_speech: the company reports what others say
- implicit_scope, missing_background, figurative, opinion: as their names say
Do not guess to avoid a flag.

Leave out: figures for other metrics; segment or product breakdowns unless you flag them as unmapped_metric; page numbers, note numbers, dates and share counts.
"""
