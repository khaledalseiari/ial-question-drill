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

# Never examined in Biology U3 since 2019, so left out: the Daphnia/caffeine practical, ethics of using
# organisms, quadrat fieldwork, serial dilutions, uncertainty and hypotheses.
# Not on the IAL spec, so left out: lenses & Kirchhoff's laws (Physics U2), Newton-Raphson (P3).
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
BIO_U2 = {
    "Eukaryotic cells & organelles": ("Cells, reproduction & development", "organelle:5, nucleus:3, nucleolus:5, mitochondri:4, rough endoplasmic:5, smooth endoplasmic:5, golgi:5, lysosome:5, centriole:5, ribosome:3, cell membrane:2, eukaryot:4, ultrastructure:5"),
    "Prokaryotic cells": ("Cells, reproduction & development", "prokaryot:5, bacteri:3, plasmid:5, capsule:4, flagell:5, pili:5, mesosome:5, 70s:5, nucleoid:5, circular dna:5"),
    "Microscopy & magnification": ("Cells, reproduction & development", "magnification:5, microscope:4, eyepiece graticule:5, graticule:5, stage micrometer:5, resolution:4, actual size:5, image size:5, micrometre:4, μm:3, scale bar:5, electron micrograph:4"),
    "Protein transport & secretion": ("Cells, reproduction & development", "secret:4, extracellular enzyme:5, vesicle:4, golgi:3, rough endoplasmic:3, exocytosis:4, modified:3, packaged:4"),
    "Mitosis & the cell cycle": ("Cells, reproduction & development", "mitosis:5, cell cycle:5, interphase:5, prophase:5, metaphase:5, anaphase:5, telophase:5, cytokinesis:5, chromatid:4, spindle:4, centromere:4, mitotic index:5, root tip:5, squash:4"),
    "Meiosis & variation": ("Cells, reproduction & development", "meiosis:5, crossing over:5, independent assortment:5, haploid:4, diploid:4, homologous:4, chiasma:5, genetic variation:5, gamete:2"),
    "Mammalian gametes & fertilisation": ("Cells, reproduction & development", "sperm:4, egg cell:4, ovum:5, acrosome:5, zona pellucida:5, cortical reaction:5, cortical granule:5, fertilisation:4, acrosome reaction:5, follicle:4"),
    "Plant fertilisation": ("Cells, reproduction & development", "pollen:5, pollen tube:5, double fertilisation:5, embryo sac:5, ovule:5, stigma:5, style:3, micropyle:5, polar nuclei:5, endosperm:5, generative nucleus:5, tube nucleus:5"),
    "Sex linkage": ("Cells, reproduction & development", "sex-linked:5, sex linked:5, x chromosome:5, y chromosome:5, x-linked:5, haemophilia:5, colour blind:5, colour-blind:5, xh:4, xb:3"),
    "Stem cells & differentiation": ("Cells, reproduction & development", "stem cell:5, totipotent:5, pluripotent:5, multipotent:5, differentiat:4, specialised:3, embryonic stem:5, induced pluripotent:5, ips:5, therapeutic:3, ethical:3"),
    "Gene expression & epigenetics": ("Cells, reproduction & development", "gene expression:5, epigenetic:5, methylation:5, acetylation:5, histone:5, transcription factor:5, lac operon:5, repressor:5, switched on:4, switched off:4, gene is expressed:4"),
    "Polygenic inheritance & environment": ("Cells, reproduction & development", "polygenic:5, continuous variation:5, discontinuous variation:5, environment:3, multifactorial:5, normal distribution:4, height:2, twin:4"),
    "Plant cell structure": ("Plant structure, biodiversity & conservation", "cell wall:4, chloroplast:4, amyloplast:5, vacuole:4, tonoplast:5, middle lamella:5, plasmodesmata:5, pit:3, plant cell:4"),
    "Starch & cellulose": ("Plant structure, biodiversity & conservation", "cellulose:5, microfibril:5, macrofibril:5, starch:4, amylose:4, amylopectin:4, β-glucose:5, beta glucose:5, α-glucose:4, glycosidic:4, hydrogen bond:2"),
    "Xylem, phloem & sclerenchyma": ("Plant structure, biodiversity & conservation", "xylem:5, phloem:5, sclerenchyma:5, lignin:5, vessel:3, sieve tube:5, companion cell:5, vascular bundle:5, stem:2"),
    "Plant fibres & sustainability": ("Plant structure, biodiversity & conservation", "plant fibre:5, tensile strength:5, sustainab:5, bioplastic:5, biofuel:4, renewable:4, starch-based:5, oil-based:4, rope:3, fibres:3"),
    "Plant mineral ions": ("Plant structure, biodiversity & conservation", "mineral ion:5, nitrate:4, magnesium:4, calcium:4, deficiency:5, chlorophyll:3, root hair:4, phosphate:3"),
    "Drugs from plants & drug testing": ("Plant structure, biodiversity & conservation", "antimicrobial:5, antibacterial:5, agar:4, aseptic:5, clear zone:5, inhibition zone:5, withering:5, digitalis:5, foxglove:5, drug testing:5, clinical trial:5, placebo:5, double blind:5, double-blind:5, phase 1:4, phase 2:4, phase 3:4"),
    "Biodiversity & its measurement": ("Plant structure, biodiversity & conservation", "biodiversity:5, species richness:5, heterozygosity:5, index of diversity:5, diversity index:5, endemic:5, genetic diversity:5, hotspot:5, quadrat:4, sampling:3"),
    "Adaptation, niche & natural selection": ("Plant structure, biodiversity & conservation", "adaptation:5, adapted:4, niche:5, natural selection:5, evolution:4, selection pressure:5, behavioural adaptation:5, physiological adaptation:5, anatomical adaptation:5, allele frequency:5"),
    "Classification & new species": ("Plant structure, biodiversity & conservation", "classification:5, taxonom:5, domain:5, kingdom:5, archaea:5, eukarya:5, phylogen:5, dna sequencing:4, dna sequence:3, protein sequence:4, new species:5, peer review:5, scientific community:5, binomial:4"),
    "Conservation (zoos & seed banks)": ("Plant structure, biodiversity & conservation", "conservation:5, zoo:5, seed bank:5, captive breeding:5, reintroduc:5, endangered:5, extinct:4, frozen zoo:5, cryopreserv:5, gene pool:4, education:3"),
}
CHEM_U2 = {
    "Enthalpy definitions & conditions": ("Energetics", "standard enthalpy change:5, enthalpy change of formation:5, enthalpy change of combustion:5, enthalpy change of neutralisation:5, enthalpy change of reaction:5, standard conditions:5, enthalpy level diagram:5, energy profile:4, exothermic:3, endothermic:3"),
    "Calorimetry experiments": ("Energetics", "calorimet:5, temperature rise:5, specific heat capacity:5, mcδt:5, mcΔt:5, polystyrene cup:5, heat loss:5, thermometer:3, insulat:4, spirit burner:5, temperature change:4"),
    "Hess's law": ("Energetics", "hess:5, enthalpy cycle:5, hess cycle:5, cannot be measured directly:5, indirect:3"),
    "Bond enthalpies": ("Energetics", "bond enthalpy:5, bond enthalpies:5, mean bond:5, bonds broken:5, bonds made:5, bond energy:5"),
    "London forces & dipoles": ("Intermolecular forces", "london force:5, london forces:5, dispersion:4, instantaneous dipole:5, induced dipole:5, permanent dipole:5, temporary dipole:5, number of electrons:4, surface contact:4, branching:4"),
    "Hydrogen bonding": ("Intermolecular forces", "hydrogen bond:5, hydrogen bonding:5, lone pair:3, ice:4, density of ice:5, anomalous:4, δ+:2, δ−:2"),
    "Boiling temperatures & solubility": ("Intermolecular forces", "boiling temperature:5, solubility:5, soluble:3, insoluble:3, miscible:5, immiscible:5, solvent:3, dissolve:3"),
    "Oxidation numbers & redox equations": ("Redox", "oxidation number:5, oxidation state:5, half-equation:5, ionic half-equation:5, redox:4, oxidising agent:5, reducing agent:5, oxidised:3, reduced:3, roman numeral:5"),
    "Disproportionation": ("Redox", "disproportionation:5, disproportionate:5, chlorate:5, chlorine and water:4, bleach:4"),
    "Group 2 chemistry": ("Inorganic chemistry", "group 2:5, magnesium:3, calcium:3, strontium:4, barium:4, thermal stability:5, thermal decomposition:5, carbonate:3, nitrate:3, hydroxide:2, solubility of:4, sulfate:2, ionic radius:3, polarising:5, polarisation:4"),
    "Group 1 & flame tests": ("Inorganic chemistry", "group 1:5, flame test:5, flame colour:5, lithium:4, sodium:2, potassium:2, rubidium:4, caesium:4, lilac:5, crimson:5, yellow-orange:5"),
    "Halogens & halides": ("Inorganic chemistry", "halogen:5, halide:5, chlorine:3, bromine:3, iodine:3, displacement:5, concentrated sulfuric acid:5, hydrogen halide:5, steamy fumes:4, purple vapour:5, hydrogen sulfide:5, sulfur dioxide:3, oxidising power:5, reducing power:5"),
    "Tests for ions": ("Inorganic chemistry", "silver nitrate:5, precipitate:4, ammonia solution:5, dilute ammonia:5, concentrated ammonia:5, barium chloride:5, limewater:5, damp red litmus:5, ammonium ion:5, cream precipitate:5, white precipitate:3, test for:4"),
    "Titrations & volumetric analysis": ("Inorganic chemistry", "titration:5, titre:5, burette:5, pipette:5, end point:5, indicator:3, thiosulfate:5, standard solution:5, volumetric flask:5, concordant:5, mean titre:5, starch indicator:5"),
    "Rates & collision theory": ("Kinetics & equilibrium", "rate of reaction:5, collision:5, collision theory:5, activation energy:5, maxwell-boltzmann:5, boltzmann:5, distribution of molecular energies:5, successful collisions:5, surface area:3, temperature:2, concentration:2"),
    "Catalysts": ("Kinetics & equilibrium", "catalyst:5, catalysis:5, heterogeneous:5, homogeneous:5, alternative route:5, alternative pathway:5, lower activation energy:5"),
    "Equilibrium & Le Chatelier": ("Kinetics & equilibrium", "equilibrium:4, le chatelier:5, dynamic equilibrium:5, position of equilibrium:5, equilibrium constant:5, kc:5, reversible:4, yield:3, haber:4, compromise:4"),
    "Alcohols": ("Organic chemistry", "alcohol:5, primary alcohol:5, secondary alcohol:5, tertiary alcohol:5, ethanol:3, propan-1-ol:4, propan-2-ol:4, butan:2, dichromate:5, oxidation of:4, aldehyde:4, ketone:4, carboxylic acid:4, phosphorus(v) chloride:5, pcl5:5, dehydration:5"),
    "Halogenoalkanes": ("Organic chemistry", "halogenoalkane:5, haloalkane:5, nucleophilic substitution:5, nucleophile:5, elimination:5, ethanolic:5, aqueous potassium hydroxide:5, hydrolysis:4, carbon–halogen:5, c–x:4, rate of hydrolysis:5, bromoalkane:5, chloroalkane:5, iodoalkane:5, ammonia:2, amine:3, nitrile:4"),
    "Organic practical techniques": ("Organic chemistry", "reflux:5, distillation:5, distil:5, separating funnel:5, anhydrous:4, drying agent:5, anti-bumping:5, condenser:4, heating under reflux:5, fractional distillation:5, purif:4, impurit:4"),
    "Mass spectrometry": ("Analytical techniques", "mass spectrum:5, mass spectrometry:5, molecular ion:5, m/z:5, fragment:5, fragmentation:5, base peak:5, m+:5"),
    "Infrared spectroscopy": ("Analytical techniques", "infrared:5, ir spectrum:5, wavenumber:5, absorption:3, c=o:4, o–h:4, o-h:4, n–h:4, fingerprint region:5, cm–1:3, cm-1:3"),
}
PHY_U2 = {
    "Progressive waves & wave equation": ("Waves", "progressive wave:5, wave equation:5, v = fλ:5, wavelength:3, frequency:2, amplitude:4, period:2, wavefront:4, oscilloscope:5"),
    "Transverse, longitudinal & phase": ("Waves", "transverse:5, longitudinal:5, compression:4, rarefaction:5, phase difference:5, in phase:5, antiphase:5, out of phase:4, radians:2"),
    "Stationary waves": ("Waves", "stationary wave:5, standing wave:5, node:5, antinode:5, fundamental:4, harmonic:5, string:3, resonance:4, tension:2"),
    "Superposition & interference": ("Waves", "superposition:5, interference:5, coherent:5, path difference:5, constructive:5, destructive:5, two sources:4, maxima:4, minima:4"),
    "Diffraction & gratings": ("Waves", "diffraction:5, diffraction grating:5, grating:4, slit:4, gap:2, d sin θ:5, d sinθ:5, order:3, lines per mm:5, electron diffraction:2"),
    "Refraction & total internal reflection": ("Waves", "refraction:5, refractive index:5, snell:5, critical angle:5, total internal reflection:5, optical fibre:5, angle of incidence:4, angle of refraction:4, glass block:4"),
    "Polarisation": ("Waves", "polaris:5, polariz:5, polaroid:5, plane-polarised:5, unpolarised:5, stress analysis:5"),
    "Doppler, ultrasound & pulse-echo": ("Waves", "doppler:5, ultrasound:5, pulse-echo:5, pulse echo:5, echo:4, reflected pulse:5, sonar:5, scan:3, blood flow:4, red shift:4"),
    "Intensity": ("Waves", "intensity:5, inverse square:5, w m-2:5, w m−2:5, power per unit area:5"),
    "Current, charge & drift velocity": ("Electricity", "current:3, charge carrier:5, drift velocity:5, i = nqva:5, nqva:5, number density:5, coulomb:3, flow of charge:5"),
    "Resistance & series/parallel": ("Electricity", "resistance:3, resistor:4, series:4, parallel:4, combined resistance:5, total resistance:5, ohm's law:5, ohm:2"),
    "Resistivity": ("Electricity", "resistivity:5, cross-sectional area:5, length of wire:4, ρ:4, micrometer:3, wire:2"),
    "EMF & internal resistance": ("Electricity", "e.m.f:5, emf:5, internal resistance:5, terminal potential difference:5, terminal p.d:5, lost volts:5, cell:3, battery:3"),
    "I-V characteristics": ("Electricity", "i-v:5, i–v:5, characteristic:4, diode:5, filament lamp:5, filament:4, ohmic:5, non-ohmic:5, light-emitting diode:5, led:3"),
    "Thermistors & LDRs": ("Electricity", "thermistor:5, ldr:5, light-dependent:5, light dependent:5, ntc:5, temperature sensor:5, light intensity:3, semiconductor:4, number of charge carriers:5"),
    "Potential dividers": ("Electricity", "potential divider:5, potential dividers:5, potentiometer:5, sensing circuit:5, output voltage:4"),
    "Electrical power & energy": ("Electricity", "power:2, electrical energy:5, energy transferred:4, p = vi:5, p = i2r:5, kilowatt:4, efficiency:3"),
    "Photoelectric effect": ("Nature of light", "photoelectric:5, work function:5, threshold frequency:5, photoelectron:5, stopping potential:5, maximum kinetic energy:5, emitted electrons:4, photocell:5"),
    "Photons & energy levels": ("Nature of light", "photon:4, energy level:5, emission spectrum:5, absorption spectrum:5, line spectrum:5, line spectra:5, excited:4, ground state:5, de-excit:5, electronvolt:4, electron volt:4, ev:2, planck:3, ionisation energy:4"),
    "Wave-particle duality": ("Nature of light", "wave-particle:5, wave–particle:5, de broglie:5, electron diffraction:5, wave nature:5, particle nature:5, duality:5"),
    "Solar cells & photovoltaics": ("Nature of light", "solar cell:5, solar panel:5, photovoltaic:5, irradiance:4, sun:2"),
}
MATHS_M1 = {
    "Constant acceleration (suvat)": ("Kinematics", "constant acceleration:5, uniform acceleration:5, decelerat:4, accelerat:2, initial speed:4, comes to rest:3, suvat:5, passes a point:4, overtake:4"),
    "Speed-time & velocity-time graphs": ("Kinematics", "speed-time graph:5, velocity-time graph:5, speed–time:5, velocity–time:5, sketch a:3, area under:4, trapezium:2, total distance:3"),
    "Vertical motion under gravity": ("Kinematics", "projected vertically:5, vertically upwards:5, vertically downwards:4, greatest height:5, released from rest:4, falls:3, ground:2, free fall:5, thrown:4, ball:2"),
    "Friction & inclined planes": ("Forces", "coefficient of friction:5, friction:4, rough:4, inclined plane:5, inclined:4, slope:4, limiting:4, about to slip:5, about to move:5, normal reaction:4, tan α:3"),
    "Statics & resolving forces": ("Forces", "equilibrium:4, resolving:5, resolve:4, resultant:4, magnitude of the force:4, string:2, tension:3, particle is in equilibrium:5, light inextensible:2, angle:2"),
    "Newton's second law (lifts, cars, tow bars)": ("Forces", "lift:5, tow bar:5, towbar:5, towrope:5, trailer:5, car:3, lorry:4, van:4, resistance:3, driving force:5, braking:4, newton's second law:5"),
    "Connected particles & pulleys": ("Forces", "pulley:5, connected:4, smooth light pulley:5, passes over:5, light inextensible string:4, hangs freely:5, string breaks:5, released from rest:2, particles a and b:3"),
    "Momentum, impulse & collisions": ("Momentum", "momentum:5, impulse:5, collide:5, collision:5, coalesce:5, direction of motion is reversed:5, speed of p:2, recoil:4, jerk:4, impact:3"),
    "Moments (beams & rods)": ("Moments", "moment:5, beam:5, rod:4, plank:5, uniform:2, non-uniform:5, support:4, centre of mass:4, about to tilt:5, tilt:4, pivot:4, resting on:3"),
    "Vectors in mechanics": ("Vectors", "i and j:5, position vector:5, velocity vector:5, bearing:4, due north:4, due east:4, i +:3, j:1, resultant force:3, ship:4, boat:3, parallel to the vector:5"),
    "Modelling assumptions": ("Modelling", "modelling assumption:5, modelled as a particle:5, model:3, light:2, inextensible:3, smooth:2, rigid:3, lamina:2, state how:2, air resistance:3"),
}
MATHS_P3 = {
    "Algebraic fractions": ("Algebra & functions", "algebraic fraction:5, simplest form:4, fully simplif:4, single fraction:5, express as a single:5"),
    "Functions: domain, range, inverse, composite": ("Algebra & functions", "domain:5, range:5, inverse:5, composite:5, f-1:5, f −1:5, fg:4, gf:4, ff:4, one-to-one:5, many-to-one:5, function:2"),
    "Modulus functions": ("Algebra & functions", "modulus:5, |x:5, |2x:5, |3x:5, |f(x)|:5, f(|x|):5, y = |:5, | =:4"),
    "Graph transformations": ("Algebra & functions", "transformation:4, sketch the graph of:3, y = f(:3, f(x + :4, 2f(:4, f(2x):4, stretch:4, translation:4, reflect:4"),
    "Exponential & log models": ("Exponentials & logarithms", "e^:2, e x:2, model:4, grows:3, decay:4, population:4, temperature:3, value of a:2, initial:3, rate of:3, years:3, minutes:3, the model:5"),
    "Solving with ln & e": ("Exponentials & logarithms", "ln:4, exact value:4, natural logarithm:5, solve:2, e2x:4, e−x:4, log:3"),
    "Logarithmic graphs (linearising)": ("Exponentials & logarithms", "log10:5, log y:5, log p:5, log a:4, straight line:4, gradient:2, intercept:4, y = axn:5, y = abx:5, ln y:4"),
    "Sec, cosec, cot & identities": ("Trigonometry", "sec:5, cosec:5, cot:5, sec2:5, cosec2:5, 1 + tan2:5, 1 + cot2:5, identity:4, prove that:3"),
    "Compound & double angle formulae": ("Trigonometry", "double angle:5, compound angle:5, sin 2:4, cos 2:4, tan 2:4, sin(a + b):5, cos(a + b):5, sin (x +:4, cos (x +:4"),
    "R cos(θ ± α) form": ("Trigonometry", "r cos:5, r sin:5, rcos:5, rsin:5, r > 0:5, 0 < α:5, α <:3, maximum value:3, minimum value:3, express:2"),
    "Inverse trig functions": ("Trigonometry", "arcsin:5, arccos:5, arctan:5, inverse trig:5"),
    "Chain, product & quotient rules": ("Differentiation", "chain rule:5, product rule:5, quotient rule:5, differentiate:4, d/dx:4, dy/dx:3, f ′(x):4, f'(x):4"),
    "Tangents, normals & stationary points": ("Differentiation", "tangent:4, normal:4, stationary point:5, turning point:5, gradient:2, maximum point:4, minimum point:4, coordinates of:2"),
    "Integration (e^x, 1/x, trig)": ("Integration", "integrate:5, integral:5, ∫:5, indefinite:4, definite:3, dx:2, exact area:4, region r:4"),
    "Iteration & change of sign": ("Numerical methods", "iteration:5, iterative:5, xn+1:5, x n + 1:5, x1 =:4, change of sign:5, sign change:5, root lies:5, interval:4, decimal places:2, show that the equation:3"),
}
MATHS_P4 = {
    "Proof by contradiction": ("Proof", "contradiction:5, proof by contradiction:5, irrational:5, assume:4, infinitely many:5, rational:2"),
    "Partial fractions": ("Algebra", "partial fraction:5, a/(:3, express in partial:5"),
    "Binomial expansion": ("Algebra", "binomial expansion:5, binomial:4, ascending powers:5, term in x:4, |x| <:5, valid:4, (1 + :2, (2 − :2, (4 + :2"),
    "Parametric equations & Cartesian form": ("Coordinate geometry", "parametric:5, parameter:4, cartesian equation:5, x = :1, y = :1, t =:2, in the form y ="),
    "Parametric differentiation": ("Differentiation", "dy/dt:4, dx/dt:4, parametric:3, tangent:3, normal:3, dy/dx:2"),
    "Implicit differentiation": ("Differentiation", "implicit:5, implicitly:5, curve c has equation:3, x2 + y2:3, xy:3, dy/dx:2"),
    "Connected rates of change": ("Differentiation", "rate of change:4, rate at which:5, increasing at a rate:5, dv/dt:4, dr/dt:5, dh/dt:4, da/dt:5, cm3 s:5, cm s:3, per second:3"),
    "Integration by substitution": ("Integration", "substitution:5, use the substitution:5, u =:3, show that ∫:3"),
    "Integration by parts": ("Integration", "by parts:5, integration by parts:5"),
    "Integration with partial fractions": ("Integration", "partial fraction:3, ln:2, hence find:2, exact value:3"),
    "Volumes of revolution": ("Integration", "volume:5, revolution:5, rotated through 2π:5, rotated through 360:5, solid of revolution:5, about the x-axis:5, πy2:5"),
    "Area & trapezium rule": ("Integration", "area:3, region r:4, trapezium rule:5, strips:5, ordinates:5, estimate:3, shaded region:4, bounded by:4"),
    "Differential equations": ("Differential equations", "differential equation:5, general solution:5, particular solution:5, separable:5, proportional to:5, rate of:3, model:3, initially:3, dv/dt:3, dp/dt:4, dn/dt:4, dθ/dt:4"),
    "Vector equations of lines": ("Vectors", "vector equation:5, line l:4, lines l1:5, l1:4, l2:4, r =:4, position vector:4, direction vector:5, intersect:5, point of intersection:5, skew:5"),
    "Angles, perpendicularity & distances": ("Vectors", "acute angle:5, angle between:5, scalar product:5, perpendicular:5, shortest distance:5, closest:5, foot of the perpendicular:5, area of triangle:4, parallelogram:4, cos θ:2"),
}
BIO_U3 = {
    "Core practical: vitamin C (DCPIP)": ("Core practicals", "vitamin c:5, dcpip:5, ascorbic acid:5"),
    "Core practical: membrane permeability (beetroot)": ("Core practicals", "beetroot:5, betalain:5, pigment:3, permeability:5, membrane:2, leak:4, ethanol concentration:4"),
    "Core practical: enzyme concentration & rate": ("Core practicals", "enzyme concentration:5, initial rate:5, trypsin:5, catalase:5, protease:4, casein:5, milk:3, hydrogen peroxide:4, enzyme:2, rate of reaction:3"),
    "Core practical: mitosis & mitotic index": ("Core practicals", "mitotic index:5, root tip:5, squash:5, mitosis:4, stain:3, toluidine:5, acetic orcein:5, hydrochloric acid:3, garlic:4, onion:3"),
    "Core practical: plant fibre tensile strength": ("Core practicals", "tensile strength:5, plant fibre:5, fibres:3, masses:3, snap:4, break:2, breaking:3"),
    "Core practical: plant mineral deficiencies": ("Core practicals", "mineral:4, deficiency:5, nitrate:4, magnesium:4, calcium:4, culture solution:5, seedlings:4, chlorosis:5"),
    "Core practical: antimicrobial properties of plants": ("Core practicals", "antimicrobial:5, antibacterial:5, inhibition zone:5, zone of inhibition:5, clear zone:5, agar plate:3, garlic:3, mint:4, plant extract:4"),
    "Microscopy & staining": ("Practical techniques", "microscope:5, magnification:5, eyepiece graticule:5, graticule:5, stage micrometer:5, field of view:5, stain:4, slide:3, cover slip:5, coverslip:5"),
    "Colorimetry & calibration curves": ("Practical techniques", "colorimeter:5, colorimetry:5, absorbance:5, transmission:5, calibration curve:5, standard curve:5, filter:3, cuvette:5"),
    "Aseptic technique": ("Practical techniques", "aseptic:5, sterile:5, sterilis:5, inoculating loop:5, bunsen:4, flame:3, contamination:4, autoclav:5"),
    "Variables & controls": ("Planning", "independent variable:5, dependent variable:5, control variable:5, controlled variable:5, control experiment:5, controlled:3, variable:3, kept constant:5, how this variable could be controlled:5"),
    "Safety & risk assessment": ("Planning", "safety:5, risk:4, hazard:5, precaution:5, goggles:5, gloves:4, irritant:5, corrosive:5, harmful:4"),
    "Accuracy, precision & repeatability": ("Data & evaluation", "accura:4, precis:4, repeatab:5, reproducib:5, reliab:4, valid:4, systematic error:5, random error:5, resolution:3"),
    "Repeats, means & anomalies": ("Data & evaluation", "anomalous:5, anomaly:5, repeat:4, mean:4, average:3, outlier:5, range:3"),
    "Graphs & lines of best fit": ("Data & evaluation", "plot a graph:5, draw a graph:5, line of best fit:5, curve of best fit:5, axes:4, graph paper:4, plot:3, scale:2, gradient:4, tangent:4"),
    "Calculations (rates, % change, means)": ("Data & evaluation", "calculate:4, percentage change:5, percentage increase:5, percentage decrease:5, rate:3, show your working:4, answer:1"),
    "Statistics (SD, correlation, tests)": ("Data & evaluation", "standard deviation:5, error bars:5, correlation:5, spearman:5, t-test:5, t test:5, statistical test:5, significant:4, significance:4, critical value:5, probability:3"),
    "Conclusions & evaluation": ("Data & evaluation", "conclusion:5, conclude:4, evaluate:4, limitation:5, improvement:5, improve:4, suggest how:3, support the hypothesis:5, extend:3, further investigation:5"),
}
SPECS = {
    ("Biology", "U1"): BIO_U1,
    ("Biology", "U2"): BIO_U2,
    ("Biology", "U3"): BIO_U3,
    ("Chemistry", "U2"): CHEM_U2,
    ("Physics", "U2"): PHY_U2,
    ("Maths", "M1"): MATHS_M1,
    ("Maths", "P3"): MATHS_P3,
    ("Maths", "P4"): MATHS_P4,
}


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
        scores, strong = {}, set()
        for point, (heading, pats) in compiled.items():
            scores[point] = sum(w * (3 * len(p.findall(text_q)) + len(p.findall(text_s)) + len(p.findall(text_a))) for p, w in pats)
            if any(w >= 5 and p.search(text_q) for p, w in pats):
                strong.add(point)  # the question itself names something specific to this point
        best = max(scores.values())
        if best < 10:
            continue
        for point, v in scores.items():
            # a card counts for a point when it is among the card's strongest matches, or - for whole
            # questions, which span several points - when the question names something specific to it
            whole = "(" not in q["label"]
            if v >= max(10, best * (0.45 if whole else 0.3)) or (whole and point in strong and v >= 10):
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
    index = []
    for (subject, unit), spec in SPECS.items():
        out = analyse(items, subject, unit, spec)
        key = f"{subject.lower()}_{unit.lower()}"
        json.dump(out, open(f"data/predict_{key}.json", "w"), separators=(",", ":"))
        index.append({"key": key, "subject": subject, "unit": unit, "papers": len(out["sessions"]),
                      "from": out["sessions"][0], "to": out["sessions"][-1]})
        print(f"\n== {subject} {unit} ({len(out['sessions'])} papers)")
        for p in sorted(out["points"], key=lambda p: (-p["freq"], p["gap"])):
            print(f'{p["status"]:10} {p["appearances"]:2}/{len(out["sessions"])}  gap {p["gap"]:2}  {p["point"]}')
    json.dump(index, open("data/predict_index.json", "w"), indent=1)


if __name__ == "__main__":
    main()
