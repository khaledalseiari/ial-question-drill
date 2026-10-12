"""Spec-point frequency analysis for the Predicted page.

For each past paper of a unit, find which spec points its questions test (keyword matching on the
question and mark-scheme text), then summarise how often and how recently each one came up.
Needs the local PDFs (download.py) and an extract.py run (data/questions.json with qp_file/ms_file)
- so run it *between* extract.py and topics.py:  extract.py -> predict.py -> topics.py

Output: data/predict_<subject>_<unit>.json
"""
import json, re
from collections import defaultdict
import pymupdf
from topics import marks_of

MONTH = {"January": 1, "May": 5, "June": 6, "October": 10, "November": 11}

# spec point -> (topic heading, keywords). The U1 core practicals (vitamin C, Daphnia, beetroot) are
# left out: on the IAL they are examined in Unit 3, and none appears in a U1 paper since 2019. Keywords as in topics.py: "phrase:weight".
BIO_U1 = {
    "Water & its properties": ("Molecules, transport & health", "water:2, dipole:5, polar molecule:5, hydrogen bond:3, solvent:4, specific heat capacity:5, cohesion:4"),
    "Carbohydrates": ("Molecules, transport & health", "monosaccharide:5, disaccharide:5, polysaccharide:5, glycosidic:5, amylose:5, amylopectin:5, glycogen:5, starch:3, glucose:2, sucrose:3, lactose:3, maltose:4, galactose:4, fructose:3, condensation:2, hydrolysis:2"),
    "Lipids (triglycerides)": ("Molecules, transport & health", "triglyceride:5, lipid:4, fatty acid:5, glycerol:5, ester bond:5, saturated:4, unsaturated:4"),
    "Mass transport & circulatory systems": ("Molecules, transport & health", "mass transport:5, surface area to volume:5, surface area:2, circulatory system:5, double circulat:5, single circulat:5, open circulat:5, closed circulat:5"),
    "Blood vessels": ("Molecules, transport & health", "artery:4, arteries:4, vein:4, capillar:4, elastic fibre:5, smooth muscle:4, lumen:4, endothelium:3, collagen:2"),
    "Blood & tissue fluid": ("Molecules, transport & health", "tissue fluid:5, plasma:3, hydrostatic pressure:5, oncotic:5, lymph:5, erythrocyte:4, red blood cell:3"),
    "Haemoglobin & O2 dissociation": ("Molecules, transport & health", "dissociation curve:5, oxygen dissociation:5, haemoglobin:3, affinity:4, bohr:5, fetal haemoglobin:5, partial pressure:4, oxyhaemoglobin:5, saturation:4"),
    "Heart structure & cardiac cycle": ("Molecules, transport & health", "cardiac cycle:5, atrium:4, atria:4, ventricle:4, systole:5, diastole:5, atrioventricular:5, semilunar:5, valve:3, heart:2, pressure change:3"),
    "Blood clotting": ("Molecules, transport & health", "clotting:5, clot:4, thrombin:5, prothrombin:5, fibrin:5, fibrinogen:5, thromboplastin:5, platelet:4, calcium ions:2"),
    "Atherosclerosis": ("Molecules, transport & health", "atherosclerosis:5, atheroma:5, plaque:4, endothelium:3, inflammatory response:4, narrowing:3"),
    "CVD risk factors & evidence": ("Molecules, transport & health", "risk factor:5, cardiovascular disease:4, cvd:4, correlation:4, causation:5, causal:4, epidemiolog:5, smoking:3, high blood pressure:4, cholesterol:3, hdl:4, ldl:4, study:1, sample size:3, data:1"),
    "CVD treatments": ("Molecules, transport & health", "antihypertensive:5, statin:5, anticoagulant:5, platelet inhibitor:5, warfarin:5, aspirin:4, beta blocker:5, ace inhibitor:5, diuretic:5, calcium channel blocker:5, side effect:4, treatment:2"),
    "Diet, energy budget & obesity": ("Molecules, transport & health", "energy budget:5, bmi:5, body mass index:5, waist-to-hip:5, waist to hip:5, obesity:4, obese:4, energy intake:5, energy output:5, diet:3, kj:2, kcal:3"),
    "Membrane structure": ("Membranes, proteins, DNA & gene expression", "fluid mosaic:5, phospholipid:4, bilayer:5, membrane:2, glycoprotein:4, glycolipid:4, cholesterol:2, channel protein:3, carrier protein:3"),
    "Transport across membranes": ("Membranes, proteins, DNA & gene expression", "diffusion:4, facilitated diffusion:5, osmosis:5, water potential:5, active transport:5, endocytosis:5, exocytosis:5, concentration gradient:4, carrier protein:3, channel protein:3, atp:2"),
    "Gas exchange surfaces": ("Membranes, proteins, DNA & gene expression", "gas exchange:5, alveol:5, fick:5, diffusion distance:5, thin:2, ventilation:4, lungs:3"),
    "Protein structure": ("Membranes, proteins, DNA & gene expression", "amino acid:4, peptide bond:5, primary structure:5, secondary structure:5, tertiary structure:5, quaternary structure:5, globular:5, fibrous:5, alpha helix:5, beta pleated:5, disulfide:5, disulphide:5, r group:4, collagen:3, haemoglobin:1"),
    "Enzymes": ("Membranes, proteins, DNA & gene expression", "enzyme:4, active site:5, activation energy:5, substrate:3, enzyme-substrate:5, induced fit:5, lock and key:5, denature:4, intracellular:3, extracellular:3"),
    "Enzyme rates & initial rate": ("Membranes, proteins, DNA & gene expression", "initial rate:5, enzyme concentration:5, rate of reaction:3, trypsin:5, catalase:5, milk:3, protease:4, tangent:4"),
    "DNA & RNA structure": ("Membranes, proteins, DNA & gene expression", "nucleotide:5, deoxyribose:5, ribose:4, phosphodiester:5, base pair:4, complementary:3, purine:5, pyrimidine:5, adenine:3, thymine:4, uracil:4, double helix:5, mrna:2, trna:2"),
    "DNA replication": ("Membranes, proteins, DNA & gene expression", "replication:5, semi-conservative:5, semiconservative:5, meselson:5, stahl:5, dna polymerase:5, helicase:5, dna ligase:5, 15n:5, 14n:5, centrifug:3"),
    "Genetic code & protein synthesis": ("Membranes, proteins, DNA & gene expression", "transcription:5, translation:5, codon:5, anticodon:5, rna polymerase:5, triplet:4, degenerate:5, non-overlapping:5, ribosome:4, start codon:5, stop codon:5, template strand:5, splicing:4, intron:4, exon:4"),
    "Mutations": ("Membranes, proteins, DNA & gene expression", "mutation:5, substitution:4, deletion:4, insertion:4, frameshift:5, point mutation:5"),
    "Monohybrid inheritance": ("Membranes, proteins, DNA & gene expression", "allele:4, genotype:5, phenotype:4, homozygous:5, heterozygous:5, dominant:4, recessive:4, monohybrid:5, genetic diagram:5, punnett:5, codominan:5, pedigree:5, probability:3, f1:4, f2:4, offspring:3"),
    "Cystic fibrosis": ("Membranes, proteins, DNA & gene expression", "cystic fibrosis:5, cftr:5, mucus:5, sticky:4, chloride ion:4, pancreas:3"),
    "Genetic screening & ethics": ("Membranes, proteins, DNA & gene expression", "genetic screening:5, screening:4, amniocentesis:5, chorionic villus:5, preimplantation:5, pgd:5, prenatal:5, embryo:3, termination:4, ethical:5, ethics:5, carrier:3, false positive:5"),
    "Gene therapy": ("Membranes, proteins, DNA & gene expression", "gene therapy:5, somatic:5, germ line:5, germline:5, liposome:5, virus vector:5, vector:3"),
}
SPECS = {("Biology", "U1"): BIO_U1}


def compile_spec(spec):
    out = {}
    for point, (heading, words) in spec.items():
        pats = []
        for w in words.split(","):
            w = w.strip()
            word, weight = (w.rsplit(":", 1) + ["1"])[:2] if re.search(r":\d$", w) else (w, "1")
            pats.append((re.compile(r"(?<![a-z])" + re.escape(word.lower())), int(weight)))
        out[point] = (heading, pats)
    return out


_docs = {}


def text_of(path, crops):
    doc = _docs.setdefault(path, pymupdf.open(path))
    parts = []
    for p, x0, y0, x1, y1 in crops:
        page = doc[p]
        clip = pymupdf.Rect(x0, y0, x1, y1)
        if page.rotation:
            clip = clip * page.derotation_matrix
        parts.append(page.get_text("text", clip=clip))
    return " ".join(parts).lower()


def session_key(s):
    month, year = s.split()
    return int(year), MONTH[month]


def analyse(items, subject, unit, spec):
    compiled = compile_spec(spec)
    items = [q for q in items if q["subject"] == subject and q["unit"] == unit]
    sessions = sorted({q["session"] for q in items}, key=session_key)
    hits = defaultdict(lambda: defaultdict(list))  # point -> session -> [question ids]
    marks = defaultdict(int)
    for q in items:
        # question text counts most; the stem and mark scheme help disambiguate
        text_q = text_of(q["qp_file"], q["q"])
        text_s = text_of(q["qp_file"], q["stem"])
        text_a = text_of(q["ms_file"], q["a"])
        scores = {}
        for point, (heading, pats) in compiled.items():
            scores[point] = sum(w * (3 * len(p.findall(text_q)) + len(p.findall(text_s)) + len(p.findall(text_a))) for p, w in pats)
        best = max(scores.values())
        if best < 10:
            continue
        for point, v in scores.items():
            if v >= max(10, best * 0.45):
                hits[point][q["session"]].append(q["id"])
                marks[point] += marks_of(q["qp_file"], q["q"], whole="(" not in q["label"])[0] or 0

    n = len(sessions)
    recent = sessions[-3:]
    points = []
    for point, (heading, _) in spec.items():
        seen = [s for s in sessions if hits[point].get(s)]
        last = seen[-1] if seen else None
        gap = (n - 1 - sessions.index(last)) if last else n  # sessions since it last appeared
        freq = len(seen) / n
        # "due": normally common, but missing from the latest papers
        if freq >= 0.85:
            status = "regular"      # in almost every paper
        elif freq >= 0.4 and gap >= 2:
            status = "due"          # normally common, missing from the latest papers
        elif freq >= 0.4:
            status = "frequent"
        elif seen and gap >= 4:
            status = "dormant"      # has come up before, but not for a while
        else:
            status = "occasional"
        points.append({
            "point": point, "heading": heading, "status": status,
            "freq": round(freq, 3), "appearances": len(seen), "last": last, "gap": gap,
            "inRecent": sum(1 for s in recent if hits[point].get(s)),
            "marks": marks[point],
            "bySession": {s: hits[point][s] for s in sessions if hits[point].get(s)},
        })
    return {"subject": subject, "unit": unit, "sessions": sessions, "points": points}


def main():
    items = json.load(open("data/questions.json"))
    if "qp_file" not in items[0]:
        raise SystemExit("run extract.py first (topics.py strips the local file paths predict.py needs)")
    for (subject, unit), spec in SPECS.items():
        out = analyse(items, subject, unit, spec)
        fn = f"data/predict_{subject.lower()}_{unit.lower()}.json"
        json.dump(out, open(fn, "w"), separators=(",", ":"))
        print(fn)
        for p in sorted(out["points"], key=lambda p: (-p["freq"], p["gap"])):
            print(f'{p["status"]:10} {p["appearances"]:2}/{len(out["sessions"])}  gap {p["gap"]:2}  {p["point"]}')


if __name__ == "__main__":
    main()
