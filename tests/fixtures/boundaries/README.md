# Sentence boundary labels

Each `.txt` file here belongs to the filing of the same name in `../documents/`.
A file holds sample passages separated by blank lines. Within a passage, each
line is one expected sentence, with runs of whitespace collapsed to one space.
The segmenter passes a passage when it produces exactly these sentences, in
this order, for that stretch of text.

**Status: proposed, awaiting confirmation by a person.** The 241 segments
were proposed by a script and reviewed once by the assistant. Under
`specs/verification.md`, a label counts only after a person confirms it.
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

Because the same process, with no person involved, proposed the labels and wrote the rules,
the present 241 of 241 agreement is not independent evidence.
