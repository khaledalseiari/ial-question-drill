"""Download Edexcel IAL question papers + mark schemes from Physics & Maths Tutor."""
import os, re, time, json, urllib.parse
import requests

BASE = "https://www.physicsandmathstutor.com/past-papers/"
UNITS = {
    ("Chemistry", "U1"): "a-level-chemistry/edexcel-unit-1",
    ("Chemistry", "U2"): "a-level-chemistry/edexcel-unit-2",
    ("Chemistry", "U3"): "a-level-chemistry/edexcel-unit-3",
    ("Chemistry", "U4"): "a-level-chemistry/edexcel-unit-4",
    ("Biology", "U1"): "a-level-biology/edexcel-unit-1",
    ("Biology", "U2"): "a-level-biology/edexcel-unit-2",
    ("Biology", "U3"): "a-level-biology/edexcel-unit-3",
    ("Psychology", "U1"): "a-level-psychology/edexcel-ial-paper-1",
    ("Psychology", "U2"): "a-level-psychology/edexcel-ial-paper-2",
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
    for (subject, unit), path in UNITS.items():
        html = S.get(BASE + path + "/", timeout=30).text
        links = sorted(set(re.findall(r'href="([^"]+\.pdf)"', html)))
        # chem/bio pages also list the legacy spec; keep the IAL 2018 spec only
        links = [l for l in links if "Edexcel-IAL" in l and ("2018-spec" in l or subject == "Psychology")]
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
