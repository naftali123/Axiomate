# Fixture filings

Ten quarterly reports (Form 10-Q) of five US-listed companies, taken unchanged
from the open dataset [`kapilrao/SEC-EDGAR`](https://huggingface.co/datasets/kapilrao/SEC-EDGAR)
on Hugging Face (Apache-2.0), revision `aa4a2334027e6b2f8c132dd698544478f61ad26a`, retrieved
on 2026-11-12. `manifest.json` holds the dataset file and SHA-256
of each; `selection.json` and `tools/fetch_fixtures.py` reproduce the extraction.

| File | Company | CIK | Period end | Filed | Accession | Format | KB |
|---|---|---|---|---|---|---|---|
| `cpa18_2021q1_10q.html` | CORPORATE PROPERTY ASSOCIATES 18 GLOBAL INC | 0001558235 | 2021-03-31 | 2021-05-10 | 0001558235-21-000013 | html | 1965 |
| `cpa18_2021q2_10q.html` | CORPORATE PROPERTY ASSOCIATES 18 GLOBAL INC | 0001558235 | 2021-06-30 | 2021-08-09 | 0001558235-21-000027 | html | 2554 |
| `cpa18_2022q1_10q.html` | CORPORATE PROPERTY ASSOCIATES 18 GLOBAL INC | 0001558235 | 2022-03-31 | 2022-05-09 | 0001558235-22-000020 | html | 1932 |
| `everi_2024q1_10q.html` | Everi Holdings Inc. | 0001318568 | 2024-03-31 | 2024-05-08 | 0001318568-24-000079 | html | 1108 |
| `geospace_fy2021q3_10q.html` | GEOSPACE TECHNOLOGIES CORP | 0001001115 | 2021-06-30 | 2021-08-06 | 0001564590-21-042009 | html | 2711 |
| `orrstown_1996q3_10q.txt` | ORRSTOWN FINANCIAL SERVICES INC | 0000826154 | 1996-09-30 | 1996-11-26 | 0000826154-96-000008 | text | 32 |
| `orrstown_1997q3_10q.txt` | ORRSTOWN FINANCIAL SERVICES INC | 0000826154 | 1997-09-30 | 1997-11-14 | 0000826154-97-000016 | text | 36 |
| `southalabama_2000q1_10q.txt` | SOUTH ALABAMA BANCORPORATION INC /DE/ | 0000783739 | 2000-03-31 | 2000-05-15 | 0000783739-00-000005 | text | 38 |
| `southalabama_2000q2_10q.txt` | SOUTH ALABAMA BANCORPORATION INC /DE/ | 0000783739 | 2000-06-30 | 2000-08-14 | 0000783739-00-000007 | text | 49 |
| `southalabama_2000q3_10q.txt` | SOUTH ALABAMA BANCORPORATION INC /DE/ | 0000783739 | 2000-09-30 | 2000-11-14 | 0000783739-00-000009 | text | 49 |

## Why these

- **Everi Holdings**: a recent HTML filing with all four metrics tagged and
  prose that states revenue and net income.
- **Geospace Technologies**: fiscal year ends on 30 September, so its quarters
  do not match calendar quarters.
- **Corporate Property Associates 18**: three filings of one company; the 2022
  first-quarter report restates the 2021 first-quarter figures.
- **South Alabama Bancorporation**: three consecutive plain-text quarters with
  figures in fixed-width tables.
- **Orrstown Financial Services**: two plain-text filings a year apart. The 1997
  report gives nine-month 1996 earnings per share as 1.64 where the 1996
  report gave 1.72, a real discrepancy for later stages.

## Known gaps

- All ten are quarterly reports. Annual reports are several times larger and
  are left for a later addition.
- Earnings press releases are not in the dataset.
- The dataset stores each filing as text, so a file here is the UTF-8 encoding
  of that text; it is not guaranteed to be byte-identical to the SEC original.
