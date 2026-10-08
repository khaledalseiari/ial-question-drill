"""Download Edexcel IAL question papers + mark schemes from Physics & Maths Tutor."""
import os, re, time, json, urllib.parse
import requests

SITE = "https://www.physicsandmathstutor.com/"
# (subject, unit) -> (PMT page, substring every kept PDF link must contain)
UNITS = {
    ("Chemistry", "U1"): ("past-papers/a-level-chemistry/edexcel-unit-1", "Edexcel-IAL/2018-spec/"),
    ("Chemistry", "U2"): ("past-papers/a-level-chemistry/edexcel-unit-2", "Edexcel-IAL/2018-spec/"),
    ("Chemistry", "U3"): ("past-papers/a-level-chemistry/edexcel-unit-3", "Edexcel-IAL/2018-spec/"),
    ("Chemistry", "U4"): ("past-papers/a-level-chemistry/edexcel-unit-4", "Edexcel-IAL/2018-spec/"),
    ("Biology", "U1"): ("past-papers/a-level-biology/edexcel-unit-1", "Edexcel-IAL/2018-spec/"),
    ("Biology", "U2"): ("past-papers/a-level-biology/edexcel-unit-2", "Edexcel-IAL/2018-spec/"),
    ("Biology", "U3"): ("past-papers/a-level-biology/edexcel-unit-3", "Edexcel-IAL/2018-spec/"),
    ("Physics", "U1"): ("past-papers/a-level-physics/edexcel-unit-1", "Edexcel-IAL/2018-spec/"),
    ("Physics", "U2"): ("past-papers/a-level-physics/edexcel-unit-2", "Edexcel-IAL/2018-spec/"),
    ("Physics", "U3"): ("past-papers/a-level-physics/edexcel-unit-3", "Edexcel-IAL/2018-spec/"),
    ("Physics", "U4"): ("past-papers/a-level-physics/edexcel-unit-4", "Edexcel-IAL/2018-spec/"),
    ("Psychology", "U1"): ("past-papers/a-level-psychology/edexcel-ial-paper-1", "Edexcel-IAL/"),
    ("Psychology", "U2"): ("past-papers/a-level-psychology/edexcel-ial-paper-2", "Edexcel-IAL/"),
    ("Maths", "P1"): ("a-level-maths-papers/c1-edexcel", "Edexcel-IAL/Pure/P1/"),
    ("Maths", "P2"): ("a-level-maths-papers/c2-edexcel", "Edexcel-IAL/Pure/P2/"),
    ("Maths", "S1"): ("a-level-maths-papers/s1-edexcel", "Edexcel-IAL/Statistics/S1/"),
    ("Maths", "P3"): ("a-level-maths-papers/c3-edexcel", "Edexcel-IAL/Pure/P3/"),
    ("Maths", "P4"): ("a-level-maths-papers/c4-edexcel", "Edexcel-IAL/Pure/P4/"),
    ("Maths", "M1"): ("a-level-maths-papers/m1-edexcel", "Edexcel-IAL/Mechanics/M1/"),
    ("Maths", "M2"): ("a-level-maths-papers/m2-edexcel", "Edexcel-IAL/Mechanics/M2/"),
}
S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 (personal revision tool)"


def key(url):
    """Normalise a QP/MS filename to its session, e.g. 'January 2019'."""
    name = urllib.parse.unquote(url.rsplit("/", 1)[1])
    m = re.search(r"(January|June|October|May|November)\s+(\d{4})", name)
    return f"{m.group(1)} {m.group(2)}" if m else None


def main():
    manifest = []
    for (subject, unit), (path, must) in UNITS.items():
        html = S.get(SITE + path + "/", timeout=30).text
        links = sorted(set(re.findall(r'href="([^"]+\.pdf)"', html)))
        # pages also list legacy / UK specs; keep only the IAL papers for this unit
        links = [l for l in links if must in l]
        qps = {key(l): l for l in links if "/QP/" in l}
        mss = {key(l): l for l in links if "/MS/" in l}
        for sess in sorted((set(qps) & set(mss)) - {None}):
            if sess is None:
                continue
            out = {}
            for kind, url in (("qp", qps[sess]), ("ms", mss[sess])):
                fn = f"pdfs/{subject}/{unit}/{sess.replace(' ', '_')}_{kind}.pdf"
                os.makedirs(os.path.dirname(fn), exist_ok=True)
                if not os.path.exists(fn):
                    r = S.get(url.replace(" ", "%20"), timeout=60)
                    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
                        print("FAIL", url, r.status_code)
                        break
                    open(fn, "wb").write(r.content)
                    time.sleep(0.5)
                out[kind] = fn
                out[kind + "_url"] = url.replace(" ", "%20")
            else:
                manifest.append({"subject": subject, "unit": unit, "session": sess, **out})
                print(subject, unit, sess)
    json.dump(manifest, open("pdfs/manifest.json", "w"), indent=1)
    print(len(manifest), "papers")


if __name__ == "__main__":
    main()
