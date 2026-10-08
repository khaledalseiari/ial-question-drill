# IAL Question Drill

Random past-paper questions from Edexcel IAL Maths P1–P4, M1, M2, S1, Physics U1–U4, Chemistry U1–U4,
Biology U1–U3 and Psychology U1–U2
(sourced from Physics & Maths Tutor). Type an answer, reveal the mark scheme, rate yourself.

Live site: https://khaledalseiari.github.io/ial-question-drill/

Filter by subject, unit and topic. Every rated attempt (with your typed answer) is logged in the
History tab in your browser, so you can revisit questions or redo the ones you missed. Topics are tagged automatically by keyword matching
(`topics.py`), so the odd question may land in the wrong topic or in "Other".

## Run locally

    python3 -m http.server 8765

then open http://localhost:8765.

The PDFs themselves are not in this repo: `data/questions.json` stores only page/crop positions,
and the browser loads each paper directly from Physics & Maths Tutor.

## Rebuild the question bank

    python3 -m venv .venv && .venv/bin/pip install pymupdf requests
    .venv/bin/python download.py   # fetch QPs + MSs into pdfs/ (skips files already there)
    .venv/bin/python extract.py    # split into question parts -> data/questions.json
    .venv/bin/python topics.py     # tag topics (run after every extract.py)

Questions are cut at the lettered-part level (e.g. Q3(a), with the Q3 stem shown above it; Maths
questions are kept whole because later parts rely on set-up text between parts) and
displayed as crops of the original PDF via PDF.js, so diagrams, structures and tables stay intact.
Two scanned Psychology papers (June 2019 U1/U2) have no text layer and are skipped.
