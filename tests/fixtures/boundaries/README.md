# Sentence boundary labels

Each `.txt` file here belongs to the filing of the same name in `../documents/`.
A file holds sample passages separated by blank lines. Within a passage, each
line is one expected sentence, with runs of whitespace collapsed to one space.
The segmenter passes a passage when it produces exactly these sentences, in
this order, for that stretch of text.

**Status: confirmed by independent cross-check (2026-11-12).** The 241 labels
were proposed by a script. Under `specs/verification.md`, a sentence-boundary
label counts when an independent tool agrees with it, and a person decides the
cases where the tool disagrees.

- Tool: pySBD 0.3.4, a rule-based splitter written by others (MIT licence),
  run by `tools/cross_check_boundaries.py`. Result in `cross_check.json`.
- The tool agrees with 236 of the 241 labels.
- The other 5 are all one kind of case: a list numbered inside a sentence,
  such as "... are: (i) Games and (ii) FinTech." The tool cuts at each item;
  the labels keep one sentence. The repository owner decided that the labels
  stand.

`cross_check.json` records the hash of every label file, and a test fails if
a label file changes afterwards. After editing a label, run the tool again.
To correct a boundary, move the line break; to reject a passage, delete it.

## Corrections made while building the segmenter

The first run of the segmenter agreed with 226 of the 238 proposed lines. Each
disagreement was read against the filing:

- 8 were segmenter faults and the rules were changed: a labelled paragraph
  such as `NOTE D:   The Company ...` (5) and a justified line with one wide
  gap (1) were taken for table rows, and a bulleted list laid out as a table
  was kept as one row (2).
- 3 were both: the `NOTE A:` paragraph in the three South Alabama files hit
  the same segmenter fault, and its label was also wrong, having left
  `... Regulation S-X. Accordingly, ...` as one sentence. Each label was split
  in two, which is why there are now 241 lines.
- 1 label lacked the bullet that opens the sentence in the stored text
  (Geospace, "• Reservoir Product Revenue – ..."); the bullet was added.

The 241 of 241 agreement between the segmenter and the labels was therefore
not independent evidence on its own; the cross-check above supplies it. It is
still weaker than a person reading every label, since two tools can share a
blind spot.
