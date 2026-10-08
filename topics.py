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

PHY_U4 = {
    "Momentum & collisions": "momentum:4, impulse:4, collision:4, collide:4, elastic:3, inelastic:4, conservation of momentum:5, recoil:3, kinetic energy:2, newton's second law:2, force-time:3",
    "Circular motion": "circular:4, angular velocity:5, angular displacement:4, radian:3, centripetal:5, rotat:3, orbit:3, revolution:3, period:1, rad s:4",
    "Electric fields": "electric field:5, field strength:3, field lines:3, coulomb's law:5, coulomb:3, point charge:4, equipotential:5, potential difference:2, electric potential:4, parallel plates:4, uniform field:3, charged sphere:4, permittivity:3",
    "Capacitors": "capacitor:5, capacitance:5, discharg:4, time constant:5, farad:4, μf:4, exponential:3, rc:3, energy stored:3",
    "Magnetic fields & induction": "magnetic field:4, magnetic flux:5, flux linkage:5, flux density:5, induced e.m.f:5, induced emf:5, induction:4, faraday:5, lenz:5, fleming:4, transformer:4, tesla:3, solenoid:3, coil:3, magnet:2, force on a current:4, cyclotron:4, generator:3, alternating:3",
    "Particle physics": "quark:5, lepton:5, baryon:5, meson:5, hadron:5, antiparticle:5, annihilation:4, pair production:5, accelerator:4, linac:5, cyclotron:3, detector:4, bubble chamber:5, neutrino:4, pion:4, kaon:4, muon:4, electron volt:3, gev:4, mev:3, rutherford:4, alpha particle scattering:5, de broglie:4, standard model:5, charge conservation:3, baryon number:5, thermionic:3",
}
MATHS_P3 = {
    "Algebra & functions": "function:3, inverse:3, composite:4, domain:4, range:4, modulus:4, |:1, f-1:4, fg:3, gf:3, algebraic fraction:4, simplify:2, transformation:3, sketch:2",
    "Exponentials & logarithms": "e x:2, ln:4, log:4, exponential:4, logarithm:4, e^:3, growth:3, decay:3, half-life:3, y = ab:3",
    "Trigonometry": "sec:4, cosec:4, cot:4, arcsin:4, arccos:4, arctan:4, sin:1, cos:1, tan:1, identity:3, r cos:5, r sin:5, double angle:4, compound angle:4, rcos:5, rsin:5, θ:1, degrees:1, radians:1",
    "Differentiation": "differentiate:4, dy/dx:4, d y:3, chain rule:5, product rule:5, quotient rule:5, gradient:3, tangent:3, normal:3, stationary:4, turning point:4, rate of change:3, derivative:3",
    "Integration": "integrate:4, integral:4, ∫:4, area:2, region:3, dx:2",
    "Numerical methods": "iteration:5, iterative:5, root:3, x n:3, xn+1:5, interval:3, change of sign:5, newton-raphson:5, convergen:3, decimal places:2, sign change:5",
}
MATHS_P4 = {
    "Partial fractions & binomial": "partial fraction:5, binomial expansion:5, binomial:4, expand:2, ascending powers:5, valid:3, |x|:4",
    "Parametric equations": "parametric:5, parameter:4, cartesian equation:4, x = :1, y = :1",
    "Implicit differentiation": "implicit:4, dy/dx:2, tangent:2, normal:2",
    "Integration": "integrate:4, integral:4, integration by parts:5, by parts:5, substitution:4, volume:4, revolution:4, area:2, region:3, trapezium rule:5, exact value:2",
    "Differential equations": "differential equation:5, dv/dt:4, dh/dt:4, dp/dt:4, dx/dt:3, rate:2, proportional:4, general solution:4, particular solution:4, separable:4",
    "Vectors": "vector:4, line l:3, lines l:3, position vector:4, intersect:3, skew:5, scalar product:5, perpendicular:3, direction:2, i + :2, j + :2, k:1, acute angle:3",
    "Proof": "proof by contradiction:5, contradiction:4, prove:2, irrational:4, rational:2",
}
MATHS_M1 = {
    "Kinematics": "constant acceleration:4, speed-time:5, velocity-time:5, displacement:3, decelerat:4, accelerat:2, suvat:4, vertically upwards:4, projected vertically:5, greatest height:4, train:3, car:2, cyclist:3, runner:3, graph:2",
    "Forces & equilibrium": "equilibrium:4, resolving:3, rough:3, smooth:2, friction:4, coefficient of friction:5, normal reaction:4, limiting:4, inclined plane:4, plane:2, tension:2, string:1, about to slip:5, about to move:5",
    "Newton's laws & connected particles": "pulley:5, connected:4, light inextensible string:4, inextensible:3, lift:4, towbar:5, tow:4, car:2, trailer:4, newton's:2, accelerat:2, released from rest:3",
    "Momentum & impulse": "momentum:5, impulse:5, collide:4, collision:4, coalesce:5, direction of motion:3, reversed:3, jerk:3",
    "Moments": "moment:5, beam:5, rod:4, plank:5, pivot:4, support:4, non-uniform:4, uniform rod:4, centre of mass:3, tilt:4, about to tilt:5",
    "Vectors in mechanics": "i and j:5, i + :3, j:2, position vector:4, velocity vector:4, bearing:3, due north:3, due east:3, resultant:3",
}
MATHS_M2 = {
    "Projectiles": "projectile:5, projected:4, angle of projection:5, above the horizontal:4, horizontal ground:3, trajectory:4, time of flight:4, range:2",
    "Work, energy & power": "work done:5, work-energy:5, kinetic energy:4, potential energy:4, power:4, kw:4, watts:4, w:1, resistance to motion:4, maximum speed:3, energy:2",
    "Centres of mass": "centre of mass:5, lamina:5, uniform lamina:5, framework:4, hangs:3, suspended:4, freely suspended:5, equilibrium:2, folded:4, wire:3, toppl:4",
    "Collisions (NEL)": "coefficient of restitution:5, restitution:5, newton's law:3, sphere:3, spheres:3, collide:3, collision:3, wall:3, rebound:4, impulse:3, momentum:3, loss of kinetic energy:4",
    "Statics of rigid bodies": "ladder:5, rod:3, rough:2, hinge:4, hinged:4, wall:2, limiting equilibrium:5, friction:2, about to slip:4, rests:2, reaction:2",
    "Kinematics with calculus": "variable acceleration:5, at time t seconds:3, t seconds:2, differentiat:4, integrat:4, dv/dt:4, velocity:2, v = :2, displacement:2, t 2:2, t2:2, comes to rest:3, instantaneous rest:5, s = :2",
}

ECON_U1 = {
    "Demand, supply & price": "demand:3, supply:3, equilibrium price:5, price mechanism:5, shift:3, excess demand:5, excess supply:5, rationing:4, signalling:4, incentive:3, market:1, complements:4, substitutes:4, derived demand:5, joint demand:5",
    "Elasticities": "elasticity:5, elastic:4, inelastic:4, ped:5, pes:5, yed:5, xed:5, cross elasticity:5, income elasticity:5, price elasticity:5, total revenue:3",
    "Consumer & producer surplus": "consumer surplus:5, producer surplus:5, indirect tax:4, subsidy:4, incidence:5, tax burden:5, specific tax:5, ad valorem:5",
    "Market failure & externalities": "market failure:5, externalit:5, negative externality:5, positive externality:5, social cost:5, social benefit:5, private cost:4, merit good:5, demerit good:5, public good:5, free rider:5, non-excludable:5, non-rival:5, information gap:5, asymmetric information:5, welfare loss:4",
    "Government intervention": "government intervention:5, government failure:5, maximum price:5, minimum price:5, price ceiling:5, price floor:5, buffer stock:5, tradable pollution permit:5, pollution permit:5, regulation:4, state provision:5, information provision:4, tax:2, subsidy:2",
    "Economic problem & specialisation": "scarcity:5, opportunity cost:5, production possibility:5, ppf:5, ppc:5, specialisation:5, division of labour:5, free market economy:5, mixed economy:5, command economy:5, rational:3, behavioural:4, money:2, positive statement:5, normative:5",
}
ECON_U2 = {
    "Measuring the economy": "gdp:4, real gdp:5, nominal:4, gdp per capita:5, gni:4, hdi:5, human development:5, inflation:3, cpi:5, rpi:4, deflation:4, unemployment:3, claimant count:5, ilo:4, labour force survey:5, balance of payments:3, current account:4, national happiness:5, well-being:4",
    "Aggregate demand & supply": "aggregate demand:5, aggregate supply:5, ad:3, sras:5, lras:5, consumption:3, investment:3, government spending:3, net exports:4, multiplier:5, marginal propensity:5, accelerator:5, keynesian:5, classical:4, output gap:5, wealth effect:4, savings:3",
    "Growth, inflation & unemployment": "economic growth:5, actual growth:4, potential growth:5, trade cycle:5, business cycle:5, recession:4, boom:3, demand-pull:5, cost-push:5, cyclical unemployment:5, structural unemployment:5, frictional:5, phillips curve:5, trade-off:4, conflict:2",
    "Macroeconomic policy": "fiscal policy:5, monetary policy:5, interest rate:4, quantitative easing:5, central bank:4, budget deficit:5, national debt:5, supply-side polic:5, supply side polic:5, taxation:3, government expenditure:4, exchange rate:2, macroeconomic objective:5, policy:1",
}
ECON_U3 = {
    "Firm objectives, size & growth": "profit maximisation:5, revenue maximisation:5, sales maximisation:5, satisficing:5, principal-agent:5, principal agent:5, organic growth:5, integration:5, horizontal integration:5, vertical integration:5, conglomerate:5, merger:5, takeover:5, demerger:5, economies of scale:4, public sector:3, private sector:3, not-for-profit:5",
    "Costs, revenue & profit": "average cost:5, marginal cost:5, fixed cost:5, variable cost:5, total cost:4, marginal revenue:5, average revenue:5, total revenue:4, normal profit:5, supernormal profit:5, losses:3, shut down:5, diseconomies:5, economies of scale:4, minimum efficient scale:5, short run:3, long run:3",
    "Market structures": "perfect competition:5, monopoly:5, monopolistic competition:5, oligopoly:5, duopoly:5, monopsony:5, concentration ratio:5, game theory:5, payoff:5, collusion:5, cartel:5, price war:5, kinked demand:5, barriers to entry:5, contestable:5, sunk cost:5, price discrimination:5, allocative efficiency:5, productive efficiency:5, dynamic efficiency:5, x-inefficiency:5",
    "Labour market": "labour market:5, wage:4, demand for labour:5, supply of labour:5, minimum wage:5, trade union:5, marginal revenue product:5, labour mobility:5, occupational:4, geographical:4, migration:3",
    "Competition policy & regulation": "competition policy:5, competition authority:5, regulation:4, regulatory capture:5, price cap:5, rpi - x:5, privatisation:5, nationalisation:5, deregulation:5, contracting out:5, competitive tendering:5",
}
ECON_U4 = {
    "Globalisation & trade": "globalisation:5, comparative advantage:5, absolute advantage:5, terms of trade:5, trading bloc:5, free trade area:5, customs union:5, common market:5, monetary union:5, wto:5, protectionism:5, tariff:5, quota:4, dumping:5, trade creation:5, trade diversion:5, export:2, import:2, multinational:4, transnational:4",
    "Balance of payments & exchange rates": "balance of payments:5, current account:5, financial account:5, capital account:5, exchange rate:5, appreciation:5, depreciation:5, devaluation:5, revaluation:5, floating:5, fixed exchange:5, competitiveness:4, marshall-lerner:5, j-curve:5, j curve:5, unit labour cost:5",
    "Poverty & inequality": "poverty:5, absolute poverty:5, relative poverty:5, inequality:5, gini:5, lorenz:5, income distribution:5, wealth:3, redistribution:5, progressive tax:5",
    "Public finance & macro policy": "public expenditure:5, public finance:5, fiscal deficit:5, budget deficit:5, national debt:5, progressive:3, regressive:4, proportional tax:5, laffer:5, fiscal policy:4, austerity:5, crowding out:5, sovereign debt:5, fiscal rule:5, macroeconomic polic:4",
    "Growth & development": "economic development:5, development:3, hdi:5, primary product:5, commodit:4, foreign direct investment:5, fdi:5, aid:4, debt relief:5, microfinance:5, fair trade:5, industrialisation:5, tourism:4, corruption:4, infrastructure:3, savings gap:5, harrod-domar:5, emerging econom:5, developing countr:4, brics:5",
    "Financial sector & role of the state": "financial market:5, bank:3, commercial bank:5, central bank:5, lender of last resort:5, money market:5, capital market:5, market bubble:5, moral hazard:5, speculation:5, systemic risk:5, regulation:3, liquidity:4, capital ratio:5, credit:3",
}
MATHS_P1 = {
    "Algebra & surds": "surd:5, rationalise:5, simplify:2, index:3, indices:4, expand:2, factorise:4, quadratic:3, completing the square:5, complete the square:5, discriminant:5, real roots:4, equal roots:4, b2 - 4ac:5, b 2 4ac:4",
    "Equations & inequalities": "inequalit:5, simultaneous:5, set of values:5, solve:2, range of values:4, region:3, satisfies:2",
    "Graphs & transformations": "sketch:4, asymptote:5, curve:2, transformation:4, translation:4, stretch:4, y = f(:4, f(x + :4, f(2x):4, intersect:3, cubic:4, reciprocal:3, crosses the:3",
    "Coordinate geometry": "straight line:5, gradient:3, perpendicular:4, parallel:3, y = mx:4, ax + by + c:5, midpoint:4, line l:3, equation of the line:5, coordinates:2",
    "Trigonometry & radians": "sine rule:5, cosine rule:5, radian:4, arc length:5, sector:5, segment:4, area of triangle:4, triangle:2, sin:1, cos:1, tan:1",
    "Differentiation": "differentiate:4, dy/dx:4, gradient of the tangent:4, tangent:3, normal:3, f'(x):4, f (x):1, derivative:3",
    "Integration": "integrate:4, integral:4, find f(x):3, ∫:4, dx:2",
}
MATHS_P2 = {
    "Proof & algebraic division": "proof:4, prove:3, factor theorem:5, remainder theorem:5, remainder:4, algebraic division:5, divide:2, factor:3, f(x) = 2x3:2",
    "Coordinate geometry of circles": "circle:5, centre:4, radius:4, tangent to the circle:5, chord:4, diameter:3",
    "Binomial expansion": "binomial:5, expansion:4, ascending powers:5, coefficient:4, term in x:4, nc:3",
    "Sequences & series": "arithmetic:5, geometric:5, series:4, sequence:4, sum to infinity:5, common ratio:5, common difference:5, nth term:4, sum of the first:5, recurrence:5, u n:3, un:2, Σ:4",
    "Exponentials & logarithms": "log:5, ln:3, logarithm:5, exponential:4, a x:2, solve 2:2",
    "Trigonometry": "trigonometric:3, identity:4, tan θ:3, sin θ:3, cos θ:3, sin 2:2, 0 ≤ θ:4, 0 θ:3, sin:1, cos:1, tan:1, radian:2",
    "Differentiation & integration": "stationary:4, maximum:3, minimum:3, increasing:4, decreasing:4, second derivative:5, d2y:5, integrate:4, area:3, region:4, trapezium rule:5, definite integral:4",
}
MATHS_S1 = {
    "Data representation & summary": "mean:3, median:4, quartile:5, interquartile:5, standard deviation:4, variance:3, box plot:5, histogram:5, stem and leaf:5, outlier:5, skew:5, frequency density:5, interpolation:5, coding:5, coded:5, Σx:3, sx:2",
    "Probability": "probability:3, venn diagram:5, independent:4, mutually exclusive:5, tree diagram:5, conditional:5, given that:3, p(a:4, p(b:4, p(a ∩:5, p(a ∪:5",
    "Correlation & regression": "correlation:5, product moment:5, regression:5, regression line:5, sxx:5, sxy:5, syy:5, explanatory:5, response variable:5, extrapolation:5, interpolate:3, y = a + bx:5",
    "Discrete random variables": "random variable:4, discrete:4, probability distribution:5, e(x):5, var(x):5, e(x2):5, cumulative distribution:5, f(x):1, discrete uniform:5, e(2x:4",
    "Normal distribution": "normal distribution:5, n(:3, ~ n:4, z:2, standard normal:5, percentage points:4, φ:3, μ:3, σ:3, upper quartile:2",
}
PHY_U1 = {
    "Motion & kinematics": "velocity:3, acceleration:3, displacement:3, speed:2, velocity-time:5, displacement-time:5, suvat:4, free fall:4, projectile:5, horizontally:3, vertically:2, scalar:4, vector:3, resolve:3, component:3, terminal velocity:2",
    "Forces & Newton's laws": "newton's first:5, newton's second:5, newton's third:5, free-body:5, free body:5, resultant force:4, weight:2, normal contact:4, tension:3, friction:2, drag:3, equilibrium:3, moment:4, centre of gravity:4, principle of moments:5, torque:4, couple:3",
    "Momentum": "momentum:5, conservation of momentum:5, collision:4, collide:4, impulse:3, recoil:4",
    "Work, energy & power": "work done:5, kinetic energy:4, gravitational potential energy:5, potential energy:3, power:3, efficiency:4, efficient:3, energy:1, conservation of energy:4, watt:3",
    "Fluids": "density:4, upthrust:5, archimedes:5, viscosity:5, viscous:4, stokes:5, laminar:5, turbulent:5, terminal velocity:4, falling-ball:5, fluid:4, flow:2, streamline:5",
    "Materials": "hooke:5, extension:4, spring:3, stiffness:4, stress:4, strain:4, young modulus:5, young's modulus:5, elastic limit:5, limit of proportionality:5, yield point:5, plastic:4, elastic:3, brittle:5, ductile:5, hard:2, tough:4, malleable:5, breaking stress:5, ultimate tensile:5, elastic strain energy:5, force-extension:5, stress-strain:5, wire:2",
}
PHY_U2 = {
    "Waves": "wave:3, wavelength:3, frequency:2, amplitude:3, transverse:5, longitudinal:5, progressive:4, phase:3, oscilloscope:4, pulse-echo:5, ultrasound:5, doppler:5, speed of sound:3, intensity:3",
    "Superposition & stationary waves": "superposition:5, stationary wave:5, standing wave:5, node:5, antinode:5, interference:5, coherent:5, path difference:5, fundamental:3, harmonic:4, string:2, constructive:4, destructive:4",
    "Refraction, diffraction & polarisation": "refraction:5, refractive index:5, critical angle:5, total internal reflection:5, snell:5, diffraction:5, diffraction grating:5, polaris:5, polariz:5, lens:4, focal length:5, power of a lens:5, real image:4, virtual image:4, magnification:3, optical fibre:4, reflection:2",
    "Electric circuits": "current:3, potential difference:4, p.d:3, resistance:3, resistor:4, ohm:3, series:3, parallel:3, kirchhoff:5, potential divider:5, internal resistance:5, e.m.f:4, emf:4, terminal potential:5, ammeter:3, voltmeter:3, circuit:3, charge:2, drift velocity:5, i = nqva:5, power:1, electrical energy:3",
    "Resistivity & I-V characteristics": "resistivity:5, i-v:5, i–v:5, characteristic:3, thermistor:5, ldr:5, light-dependent:5, diode:4, filament:4, ntc:5, semiconductor:4, metal:2, temperature:2, conductor:3",
    "Particle nature of light": "photon:5, photoelectric:5, work function:5, threshold frequency:5, planck:4, electronvolt:4, electron volt:4, ev:2, energy level:5, emission spectrum:5, absorption spectrum:5, line spectr:5, wave-particle:5, wave–particle:5, de broglie:5, electron diffraction:5, quantum:3, excitation:4, ionisation:3, solar cell:3",
}
PHY_PRACTICAL = {
    "Measurement & uncertainties": "uncertainty:5, uncertainties:5, percentage uncertainty:5, precision:4, precise:3, accuracy:3, accurate:3, micrometer:5, vernier:5, calipers:5, ruler:3, resolution:4, systematic error:5, random error:5, zero error:5, parallax:5, repeat:3, mean:3, average:3, safety:4, significant figures:3, plan:3, procedure:3, variable:3, control:2, determine:2",
}

TOPICS = {
    ("Economics", "U1"): ECON_U1,
    ("Economics", "U2"): ECON_U2,
    ("Economics", "U3"): ECON_U3,
    ("Economics", "U4"): ECON_U4,
    ("Physics", "U1"): PHY_U1,
    ("Physics", "U2"): PHY_U2,
    ("Physics", "U3"): {**PHY_U1, **PHY_U2, **PHY_PRACTICAL},  # practical paper: draws on U1 + U2
    ("Physics", "U4"): PHY_U4,
    ("Maths", "P1"): MATHS_P1,
    ("Maths", "P2"): MATHS_P2,
    ("Maths", "S1"): MATHS_S1,
    ("Maths", "P3"): MATHS_P3,
    ("Maths", "P4"): MATHS_P4,
    ("Maths", "M1"): MATHS_M1,
    ("Maths", "M2"): MATHS_M2,
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
