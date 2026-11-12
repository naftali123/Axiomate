# Sentence boundary labels

Each `.txt` file here belongs to the filing of the same name in `../documents/`.
A file holds sample passages separated by blank lines. Within a passage, each
line is one expected sentence, with runs of whitespace collapsed to one space.
The segmenter passes a passage when it produces exactly these sentences, in
this order, for that stretch of text.

**Status: proposed, awaiting confirmation by a person.** The 238 segments
were proposed by a script and reviewed once by the assistant. Under
`specs/verification.md`, a label counts only after a person confirms it.
To correct a boundary, move the line break; to reject a passage, delete it.
