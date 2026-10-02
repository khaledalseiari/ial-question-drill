"""Tag each question with spec topics by keyword-matching its text (and, more weakly, its mark scheme).

Reads data/questions.json (from extract.py), adds "topics", drops local file paths, writes it back.
"""
import json, re
from collections import Counter
import pymupdf

# keyword -> weight is 1 unless written "word:N". Matching is case-insensitive on word starts.
CHEM_AS = {
    "Moles & equations": "mol, moles, g of:2, deduce the overall equation:3, equation:1, heated:1, water of crystallisation:3, xh2o:4, mass:1, mass of, molar mass, concentration, titration, titre, yield, atom economy, empirical formula, molecular formula, avogadro, volume of gas, pv = nrt, ideal gas, percentage, burette, pipette, cm3:2, dm3, ionic equation, water of crystallisation",
    "Atomic structure & periodic table": "isotope:3, ionisation energy:4, ionization energy:4, electronic configuration:3, orbital:2, sub-shell:2, subshell:2, proton, neutron, electron, mass spectrum:2, relative atomic mass:2, periodicity:3, atomic radius:2, period 3:2, s-block, d-block, p-block, mass number, mass spectrometer:4, ionised:2, ionized:2, element:1, ion:1",
    "Bonding & structure": "ionic bond:3, covalent:2, dative:3, metallic:2, electronegativity:3, polar:2, dipole, shape of, bond angle:3, lone pair:3, giant, lattice:2, graphite:2, diamond:2, graphene:2, delocalised, sigma:2, pi bond:2, melting temperature, electron density, dot-and-cross:3",
    "Alkanes, alkenes & polymers": "alkane:3, alkene:3, crude oil:3, cracking:3, reforming:3, fuel:2, combustion, free radical:3, radical:2, e-z:3, e/z:3, isomer:2, electrophilic addition:3, bromine water:2, polymer:3, polymerisation:3, homologous:2, skeletal formula:2, iupac, petrol, carbocation:2, hydrocarbon:3, pollutant:3, pollution:3, carbon monoxide:3, acid rain:3, catalytic converter:4, initiation:3, propagation:3, termination:3, br2:2, ch3:1, ch2:1, c2h:1, c3h:1, c4h:1, c5h:1, c6h:1, major product:3, biofuel:4, carbon neutral:4, ozone:2, nox:3, sulfur dioxide:2, squalane:2, cyclo:2, cis:2, trans:2, unsaturated:2, saturated:2",
    "Energetics": "enthalpy change:3, enthalpy:2, exothermic:2, endothermic:2, hess:4, bond enthalpy:3, calorimetry:3, temperature rise:2, ΔH:2, enthalpy of combustion:3, enthalpy of formation:3, neutralisation:2, specific heat:3",
    "Intermolecular forces": "intermolecular:3, hydrogen bond:4, london force:4, london forces:4, dispersion:3, permanent dipole:3, boiling temperature:2, solubility:2, soluble:1, miscible:2",
    "Redox": "oxidation number:4, redox:3, oxidising agent:3, reducing agent:3, oxidised:2, reduced:2, disproportionation:4, half-equation:3, oxidation state",
    "Groups 1, 2 & 7": "group 1:3, group 2:3, group 7:3, halogen:3, halide:3, chlorine:2, bromine:2, iodine:2, silver nitrate:3, flame test:4, thermal stability:3, carbonate:2, nitrate:2, hydroxide:1, sulfate:1, barium, magnesium, calcium, strontium, chlorate:3, hydrogen halide:3",
    "Kinetics & equilibrium": "rate of reaction:3, rate:2, activation energy:4, catalyst:3, maxwell-boltzmann:4, boltzmann:4, collision:3, equilibrium:3, le chatelier:4, dynamic equilibrium:3, position of equilibrium:3, kc:3, yield:1",
    "Alcohols & halogenoalkanes": "alcohol:3, halogenoalkane:4, haloalkane:4, nucleophilic substitution:4, nucleophile:3, elimination:3, primary:1, secondary:1, tertiary:1, acidified potassium dichromate:4, dichromate:3, reflux:2, distillation:2, aldehyde:2, ketone:2, carboxylic acid:2, ethanol:2, hydrolysis:2",
    "Mass spec & IR": "infrared:4, ir spectrum:4, wavenumber:4, absorption:2, mass spectrum:3, molecular ion:4, fragment:3, m/z:4, greenhouse:2",
}
CHEM_A2 = {
    "Rates (kinetics II)": "rate equation:4, order:3, rate constant:4, half-life:3, rate-determining:4, initial rate:3, clock:2, mechanism:2, arrhenius:4, rate:1, continuous monitoring:4, colorimetry:3, heterogeneous catalyst:4, catalyst:2, explodes:2",
    "Entropy & energetics II": "entropy:4, lattice energ:4, lattice enthalp:4, born-haber:5, enthalpy of hydration:4, hydration:3, enthalpy of solution:4, gibbs:4, feasible:3, ΔS:3, ΔG:3, polarisation:3, electron affinity:3, atomisation:3, enthalpy change of formation:3, δfh:3, ΔfH:3",
    "Equilibria (Kc, Kp)": "kc:3, kp:4, partial pressure:4, mole fraction:4, equilibrium constant:4, equilibrium:2, heterogeneous:2, homogeneous:2",
    "Acids, bases & buffers": "ph:3, buffer:4, ka:4, pka:4, kw:4, weak acid:3, strong acid:3, strong base:2, titration curve:4, indicator:3, conjugate:3, brønsted:3, bronsted:3, equivalence point:3, neutralisation:2",
    "Optical isomerism": "chiral:4, optical isomer:4, enantiomer:4, racemic:4, plane-polarised:4, plane polarised:4, stereoisomer:3",
    "Carbonyls, acids & derivatives": "aldehyde:3, ketone:3, carbonyl:3, dnph:4, tollens:4, fehling:4, hydrogen cyanide:3, hcn:3, nucleophilic addition:4, iodoform:4, carboxylic acid:3, ester:3, acyl chloride:4, polyester:3, lialh4:3, nabh4:3, hydrolysis:2, esterification:3, amide:4, amine:3, ethanoic:2, propanoic:2, butanoic:2, ethanal:3, propanal:3, propanone:3, butanal:3, butanone:3, -al:1, -one:1, pale yellow precipitate:3, iodine and sodium hydroxide:4, iodine dissolved in aqueous:4, coo:2, cooh:2, coci:3, oate:3, hydrolysed:2, anhydride:4",
    "Spectroscopy & chromatography": "nmr:4, chemical shift:4, splitting:3, singlet:3, doublet:3, triplet:3, quartet:3, tms:3, chromatography:4, rf value:3, hplc:4, gas chromatography:4, mass spectrum:2, infrared:2, peaks:2",
}
BIO_U1 = {
    "Biological molecules": "carbohydrate:3, glucose:2, monosaccharide:3, disaccharide:3, polysaccharide:3, starch:2, glycogen:3, glycosidic:4, lipid:3, triglyceride:4, fatty acid:3, ester bond:3, saturated:2, protein:2, amino acid:2, peptide bond:3, condensation:3, hydrolysis:2, haemoglobin:2, globular:3, fibrous:3, collagen:3, water:1",
    "Heart & circulation": "heart:3, cardiac:3, atrium:3, ventricle:3, artery:3, arteries:3, vein:2, capillar:3, blood pressure:3, valve:3, ecg:4, circulation:3, aorta:3, tissue fluid:4, blood vessel:3, mass transport:3, double circulatory:4",
    "Blood & clotting": "blood clot:4, clotting:4, thrombin:4, fibrin:4, platelet:4, prothrombin:4, thromboplastin:4, oxygen dissociation:4, haemoglobin:2, erythrocyte:3, red blood cell:3",
    "CVD & risk factors": "cardiovascular disease:4, cvd:4, atherosclerosis:4, atheroma:4, risk factor:4, cholesterol:3, ldl:3, hdl:3, obesity:3, bmi:4, diet:2, hypertension:3, statin:4, anticoagulant:4, antihypertensive:4, plaque:3, coronary:3, stroke:2, energy budget:4, waist-to-hip:4, correlation:2, causation:2, epidemiolog:3",
    "Membranes & transport": "membrane:3, phospholipid:4, fluid mosaic:4, diffusion:3, facilitated diffusion:4, osmosis:4, active transport:4, endocytosis:4, exocytosis:4, channel protein:3, carrier protein:3, permeability:3, water potential:3, gas exchange:3, surface area:2, alveol:3",
    "Enzymes": "enzyme:4, active site:4, substrate:3, activation energy:3, inhibitor:3, denature:3, enzyme-substrate:4, catalase:3, initial rate:3, lock and key:3, induced fit:4",
    "DNA & protein synthesis": "dna:3, rna:3, mrna:4, trna:4, transcription:4, translation:4, codon:4, anticodon:4, nucleotide:3, replication:3, semi-conservative:4, meselson:4, base pair:3, ribosome:2, gene:1, triplet code:4, polypeptide:2, rna polymerase:4, dna polymerase:4, helicase:4, mutation:3",
    "Inheritance & genetic disorders": "allele:4, genotype:4, phenotype:3, homozygous:4, heterozygous:4, dominant:3, recessive:3, monohybrid:4, cystic fibrosis:4, genetic screening:4, gene therapy:4, pedigree:4, carrier:2, punnett:4, prenatal:3, amniocentesis:4, chorionic villus:4, pgd:4, codominan:4, sickle cell:3",
}
BIO_U2 = {
    "Cell structure & microscopy": "organelle:3, nucleus:2, mitochondri:3, rough endoplasmic:4, endoplasmic reticulum:4, golgi:4, lysosome:4, ribosome:2, centriole:4, prokaryot:4, eukaryot:3, microscope:3, magnification:4, eyepiece graticule:4, graticule:4, stage micrometer:4, nucleolus:3, cell wall:2, plasmid:3, capsule:2, flagell:3, protein transport:3",
    "Cell division (mitosis & meiosis)": "mitosis:4, meiosis:4, cell cycle:4, interphase:4, prophase:4, metaphase:4, anaphase:4, telophase:4, cytokinesis:4, chromosome:2, chromatid:4, mitotic index:4, root tip:3, crossing over:4, independent assortment:4, haploid:3, diploid:3, homologous:3",
    "Reproduction & fertilisation": "gamete:3, sperm:4, egg:3, ovum:4, acrosome:4, zona pellucida:4, fertilisation:4, cortical:4, pollen:4, pollen tube:4, double fertilisation:4, embryo sac:4, zygote:3, linkage:3, sex-linked:4, sex linked:4, x chromosome:3",
    "Stem cells & gene expression": "stem cell:4, totipotent:4, pluripotent:4, multipotent:4, differentiation:4, specialised:3, epigenetic:4, methylation:4, acetylation:4, histone:4, transcription factor:4, gene expression:4, lac operon:4, phenotype:2, environment:1, polygenic:4, continuous variation:3, discontinuous:3",
    "Plant structure & products": "xylem:4, phloem:4, sclerenchyma:4, plant fibre:4, cellulose:4, starch:2, amylose:3, amylopectin:3, microfibril:4, middle lamella:4, plasmodesmata:4, pit:2, chloroplast:3, amyloplast:4, vacuole:3, tonoplast:4, lignin:4, sustainab:3, bioplastic:4, tensile strength:4, stem:2, plant cell:3",
    "Drugs from plants & testing": "antimicrobial:4, bacteria:2, agar:3, inhibition:3, clear zone:4, drug testing:4, clinical trial:4, placebo:4, double blind:4, double-blind:4, withering:4, digitalis:4, phase 1:3, phase 2:3, phase 3:3, aseptic:4, mineral:3, nitrate:2, magnesium:2, calcium:2, deficiency:3",
    "Biodiversity & classification": "biodiversity:4, species richness:4, heterozygosity:4, diversity index:4, endemic:4, habitat:3, niche:4, adaptation:3, adapted:2, natural selection:4, evolution:3, classification:4, domain:3, kingdom:3, taxonomy:4, phylogen:4, dna sequencing:3, new species:3, peer review:3, genetic diversity:3, quadrat:3, sampling:2",
    "Conservation": "conservation:4, zoo:4, seed bank:4, captive breeding:4, reintroduc:4, endangered:4, extinct:3, genetic diversity:2, frozen:2, education:2, cryopreserv:4",
}
PSY_U1 = {
    "Obedience": "obedience:4, obey:4, milgram:4, agentic:4, agency theory:4, legitimate authority:4, autonomous:3, moral strain:4, burger:3, hofling:4, authoritarian personality:4, adorno:3, destructive obedience:4, momentum of compliance:4",
    "Prejudice": "prejudice:4, social identity theory:4, social identity:4, in-group:4, ingroup:4, out-group:4, outgroup:4, realistic conflict:4, sherif:4, robbers cave:4, tajfel:4, discriminat:3, categorisation:3, superordinate:4, reicher:3, haslam:3, culture:2, conformity:3",
    "Memory": "memory:3, multi-store:4, multistore:4, working memory:4, short-term:3, long-term:3, episodic:4, semantic:4, procedural:3, reconstructive:4, bartlett:4, war of the ghosts:4, schema:4, baddeley:4, central executive:4, phonological:4, visuospatial:4, episodic buffer:4, hm:3, clive wearing:4, capacity:3, duration:3, encoding:3, recall:2, forget:2, sebastian:3, schmolck:4, steyvers:3, tulving:4",
    "Research methods & statistics": "questionnaire:3, interview:3, open question:3, closed question:3, likert:4, rating scale:3, sampling:3, random sample:3, opportunity sample:3, volunteer:3, stratified:3, reliability:3, validity:3, hypothesis:3, null:3, alternative hypothesis:4, mann-whitney:4, chi-squared:4, wilcoxon:4, spearman:4, mean:2, median:2, mode:2, range:2, standard deviation:4, significance:3, critical value:4, experimental design:4, independent groups:4, repeated measures:4, matched pairs:4, counterbalanc:4, qualitative:3, quantitative:3, thematic analysis:4, correlation:3, ethic:3, bps:3, informed consent:3, right to withdraw:3, debrief:3, deception:3, laboratory experiment:3, field experiment:3, demand characteristics:3",
}
PSY_U2 = {
    "Biological psychology": "brain:3, amygdala:4, prefrontal:4, cortex:3, limbic:4, hormone:3, testosterone:4, cortisol:3, aggression:4, aggressive:3, raine:4, brendgen:4, neurotransmitter:4, synapse:4, synaptic:4, receptor:3, serotonin:4, dopamine:4, freud:4, psychodynamic:4, catharsis:4, eros:4, thanatos:4, evolution:3, natural selection:3, circadian:4, infradian:4, ultradian:4, rhythm:3, menstrual:3, sleep:3, brain scan:4, pet scan:4, fmri:4, ct scan:4, mri:4, central nervous system:4, li:1, twin stud:4, adoption:3, heritability:3",
    "Recreational drugs": "recreational drug:4, drug:3, cannabis:4, heroin:4, ecstasy:4, mdma:4, cocaine:4, nicotine:4, alcohol:3, agonist:4, antagonist:4, reuptake:4, tolerance:4, withdrawal:4, addiction:4",
    "Learning: conditioning": "classical conditioning:5, operant conditioning:5, pavlov:4, conditioned stimulus:4, unconditioned:4, conditioned response:4, extinction:3, spontaneous recovery:4, generalisation:3, reinforcement:4, reinforce:3, punishment:4, skinner:4, watson:4, little albert:4, phobia:4, systematic desensitisation:5, flooding:5, token economy:5, shaping:3, schedule of reinforcement:4, variable ratio:4, fixed interval:4, behaviourism:3, behaviourist:3",
    "Learning: social learning": "social learning:5, bandura:5, bobo doll:5, modelling:4, model:2, imitation:4, imitate:4, vicarious:4, observational learning:4, role model:4, attention:2, retention:3, reproduction:2, motivation:2, becker:4, capafons:4",
    "Research methods & statistics": PSY_U1["Research methods & statistics"] + ", animal:3, animals:3, rat:2, lab experiment:3, observation:3, covert:3, overt:3, participant observation:4, tally:3, inter-rater:4, inter-observer:4, content analysis:4, case study:2, twin:2, scientific:2, objectivity:3, replicab:3, falsif:3",
}

TOPICS = {
    ("Chemistry", "U1"): {k: CHEM_AS[k] for k in ["Moles & equations", "Atomic structure & periodic table", "Bonding & structure", "Alkanes, alkenes & polymers"]},
    ("Chemistry", "U2"): {k: CHEM_AS[k] for k in ["Energetics", "Intermolecular forces", "Redox", "Groups 1, 2 & 7", "Kinetics & equilibrium", "Alcohols & halogenoalkanes", "Mass spec & IR", "Moles & equations"]},
    ("Chemistry", "U3"): CHEM_AS,  # practical paper: draws on all of U1 + U2
    ("Chemistry", "U4"): CHEM_A2,
    ("Biology", "U1"): BIO_U1,
    ("Biology", "U2"): BIO_U2,
    ("Biology", "U3"): {**BIO_U1, **BIO_U2},  # practical paper: draws on U1 + U2
    ("Psychology", "U1"): PSY_U1,
    ("Psychology", "U2"): PSY_U2,
}


def compile_topics(spec):
    out = {}
    for topic, words in spec.items():
        pats = []
        for w in words.split(","):
            w = w.strip()
            if len(w) < 2 or w.isdigit():
                continue
            word, _, weight = w.rpartition(":") if re.search(r":\d$", w) else (w, "", "1")
            pats.append((re.compile(r"(?<![a-z])" + re.escape(word.lower())), int(weight)))
        out[topic] = pats
    return out


COMPILED = {k: compile_topics(v) for k, v in TOPICS.items()}
_docs = {}


def text_of(path, crops):
    if path not in _docs:
        _docs[path] = pymupdf.open(path)
    doc = _docs[path]
    parts = []
    for p, x0, y0, x1, y1 in crops:
        page = doc[p]
        clip = pymupdf.Rect(x0, y0, x1, y1)
        if page.rotation:
            clip = clip * page.derotation_matrix
        parts.append(page.get_text("text", clip=clip))
    return " ".join(parts).lower()


def score(spec, text):
    return {t: sum(w * len(p.findall(text)) for p, w in pats) for t, pats in spec.items()}


def main():
    items = json.load(open("data/questions.json"))
    counts = Counter()
    for it in items:
        spec = COMPILED[(it["subject"], it["unit"])]
        s = Counter()
        for src, weight in ((text_of(it["qp_file"], it["q"]), 3), (text_of(it["qp_file"], it["stem"]), 2), (text_of(it["ms_file"], it["a"]), 1)):
            for t, v in score(spec, src).items():
                s[t] += v * weight
        best = s.most_common(1)[0][1] if s else 0
        if best < 3:
            topics = ["Other"]
        else:
            topics = [t for t, v in s.most_common(2) if v >= best * 0.7]
        it["topics"] = topics
        for t in topics:
            counts[(it["subject"], it["unit"], t)] += 1
        del it["qp_file"], it["ms_file"]
    json.dump(items, open("data/questions.json", "w"), separators=(",", ":"))
    for k, v in sorted(counts.items()):
        print(*k, v, sep=" | ")


if __name__ == "__main__":
    main()
