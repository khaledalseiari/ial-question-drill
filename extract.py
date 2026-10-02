"""Split each QP into question parts and match each part to its mark-scheme region.

Output: data/questions.json, a list of items with page-region crops (in PDF points)
that the website renders client-side with PDF.js. No text is re-typed.
"""
import json, re, string
import pymupdf

TOP = 40  # skip running header; BOTTOM/X0/X1 are set per document (A4 vs Letter)
BOTTOM, MARGIN, RIGHT = 792, 28, 28
DIMS = {}  # page -> (width, height) in displayed orientation

Q_RE = re.compile(r"^(\d{1,2})(?:\s+|\s*(?=\())(.*)$")
PART_RE = re.compile(r"^\(([a-z])\)")
END_RE = re.compile(r"^\(Total for Question|^TOTAL FOR (SECTION|PAPER)|^BLANK PAGE|^Use this space for any rough")
DOTS = re.compile(r"^(\d\s*)?[.\u2026 ]{8,}$")
MS_LABEL_RE = re.compile(r"^(\d{1,2})\s*(?:\(?([a-h])\)?)?(?:\s*\(?([ivx]+)\)?)*\s*$")


def lines(doc):
    """All text lines as (page, x, y0, y1, size, text), in reading order."""
    out = []
    for pn, page in enumerate(doc):
        rot = page.rotation_matrix  # landscape mark-scheme pages: use displayed coords
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                t = "".join(s["text"] for s in l["spans"]).replace("\t", " ").strip()
                if not t or t == "PMT":
                    continue
                x, y0, _, y1 = pymupdf.Rect(l["bbox"]) * rot if page.rotation else l["bbox"]
                out.append((pn, x, y0, y1, max(s["size"] for s in l["spans"]), t))
    out.sort(key=lambda r: (r[0], round(r[2]), r[1]))
    return out


def bottom(p):
    return DIMS[p][1] - 48


def content_bottom(lns, pn, after, before):
    ys = [y1 for p, x, y0, y1, s, t in lns if p == pn and after <= y0 < before and y1 < bottom(pn)]
    return min(max(ys, default=after) + 6, before)


def span(lns, start, end):
    """Crops from (page, y) start to (page, y) end, split across pages."""
    (p0, y0), (p1, y1) = start, end
    crops = []
    for p in range(p0, p1 + 1):
        top = y0 if p == p0 else TOP
        bot = y1 if p == p1 else bottom(p)
        if p != p1:
            bot = content_bottom(lns, p, top, bot)
        page_lines = [t for pp, x, a, b, s, t in lns if pp == p and top <= a < bot]
        if any("BLANK PAGE" in t for t in page_lines) or not page_lines:
            continue
        # drop trailing dotted answer lines - the user types their answer instead
        inside = [(a, t) for pp, x, a, b, s, t in lns if pp == p and top <= a < bot]
        while inside and DOTS.match(inside[-1][1]):
            bot = inside.pop()[0] - 2
        if bot - top > 12:
            crops.append([p, MARGIN, round(top, 1), round(DIMS[p][0] - RIGHT, 1), round(min(bot, bottom(p)), 1)])
    return crops


def set_frame(doc, qx, right=None):
    """Page geometry differs between papers; derive crop bounds from page size and question column."""
    global BOTTOM, MARGIN, RIGHT
    DIMS.clear()
    DIMS.update({p: (pg.rect.width, pg.rect.height) for p, pg in enumerate(doc)})
    BOTTOM = DIMS[0][1] - 48
    MARGIN = max(qx - 14, 0)
    RIGHT = MARGIN if right is None else right


def parse_qp(path):
    doc = pymupdf.open(path)
    lns = lines(doc)
    # question numbers sit in a fixed left column: take the most common x of "N  Text" lines
    cands = [round(x) for p, x, y0, y1, s, t in lns if s >= 10.5 and x > 25 and re.match(r"^\d{1,2}\s+[A-Z(]", t)]
    qx = max(set(cands), key=cands.count) if cands else 43
    set_frame(doc, qx)
    starts = []  # (qnum, letter|None, page, y)
    ends = []    # (page, y) hard stops
    expect = 1
    cur_q, cur_letter = None, None
    for p, x, y0, y1, size, t in lns:
        if y0 < TOP or y0 > BOTTOM:
            continue
        if END_RE.match(t):
            ends.append((p, y1 + 4 if t.startswith("(Total") else y0 - 2))
            continue
        m = Q_RE.match(t)
        if m and abs(x - qx) < 6 and size >= 10.5 and int(m.group(1)) == expect and not m.group(2).startswith("."):
            cur_q, cur_letter = expect, None
            expect += 1
            rest = m.group(2)
            pm = PART_RE.match(rest)
            if pm and pm.group(1) == "a":
                cur_letter = "a"
                starts.append((cur_q, None, p, y0 - 4))  # empty stem
                starts.append((cur_q, "a", p, y0 - 4))
            else:
                starts.append((cur_q, None, p, y0 - 4))
            continue
        pm = PART_RE.match(t)
        if pm and cur_q and qx + 8 < x < qx + 42:
            want = "a" if cur_letter is None else string.ascii_lowercase[string.ascii_lowercase.index(cur_letter) + 1]
            if pm.group(1) == want:
                cur_letter = want
                starts.append((cur_q, want, p, y0 - 4))
    last = (len(doc) - 1, bottom(len(doc) - 1))

    def stop(after, nxt):
        """Earliest hard stop between `after` and `nxt`."""
        for e in ends:
            if after < e <= nxt:
                return e
        return nxt

    segs = {}
    for i, (q, letter, p, y) in enumerate(starts):
        nxt = (starts[i + 1][2], starts[i + 1][3]) if i + 1 < len(starts) else last
        end = stop((p, y), nxt)
        segs[(q, letter)] = span(lns, (p, y), end)
    return segs


def parse_ms(path):
    doc = pymupdf.open(path)
    lns = lines(doc)
    hx = [x for p, x, y0, y1, s, t in lns if t.startswith("Question")]
    set_frame(doc, min(hx, default=43), right=12)  # mark schemes have a 'Mark' column near the edge
    labels = []  # (q, letter, page, y)
    for i, (p, x, y0, y1, size, t) in enumerate(lns):
        if y0 < 30:
            continue
        compact = t.replace(" ", "")
        m = MS_LABEL_RE.match(t) or MS_LABEL_RE.match(compact)
        if not m:
            continue
        # must sit in the 'Question Number' column; include the header row when it is directly above
        if not any(abs(hx_ - x) < 40 for hx_ in hx):
            continue
        hdr = [r for r in lns if r[0] == p and r[5].startswith("Question") and 0 < y0 - r[2] < 60 and abs(r[1] - x) < 40]
        labels.append((int(m.group(1)), m.group(2), p, (min(r[2] for r in hdr) if hdr else y0) - 6))
    labels.sort(key=lambda r: (r[2], r[3]))
    last = (len(doc) - 1, bottom(len(doc) - 1))
    segs = {}
    for i, (q, letter, p, y) in enumerate(labels):
        nxt = (labels[i + 1][2], labels[i + 1][3]) if i + 1 < len(labels) else last
        segs.setdefault((q, letter), []).extend(span(lns, (p, y), nxt))
    return segs


def main():
    manifest = json.load(open("pdfs/manifest.json"))
    items, stats = [], []
    for paper in manifest:
        try:
            qp, ms = parse_qp(paper["qp"]), parse_ms(paper["ms"])
        except Exception as e:  # noqa: BLE001
            print("ERR", paper["qp"], e)
            continue
        matched = 0
        for (q, letter), crops in qp.items():
            if letter is None and (q, "a") in qp:
                continue  # stems are shown with each part, not on their own
            ms_crops = ms.get((q, letter)) or (ms.get((q, None)) if letter is None else None)
            if not ms_crops and letter is None:  # MCQ/whole question marked by sub-labels
                ms_crops = [c for (mq, ml), cs in sorted(ms.items(), key=lambda kv: str(kv[0][1])) if mq == q for c in cs]
            if not crops or not ms_crops:
                continue
            stem = qp.get((q, None), []) if letter else []
            items.append({
                "id": f"{paper['subject'][:3]}-{paper['unit']}-{paper['session'].replace(' ', '')}-{q}{letter or ''}",
                "subject": paper["subject"], "unit": paper["unit"], "session": paper["session"],
                "label": f"Q{q}" + (f"({letter})" if letter else ""),
                "qp": paper["qp_url"], "ms": paper["ms_url"],
                "qp_file": paper["qp"], "ms_file": paper["ms"],
                "stem": stem, "q": crops, "a": ms_crops,
            })
            matched += 1
        parts = sum(1 for (q, l) in qp if not (l is None and (q, "a") in qp))
        stats.append((paper["qp"], parts, matched))
        if parts == 0 or matched / parts < 0.7:
            print(f"LOW  {paper['qp']}: {matched}/{parts}")
    json.dump(items, open("data/questions.json", "w"), separators=(",", ":"))
    print(len(items), "questions from", len(stats), "papers")


if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)
    main()
