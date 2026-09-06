"""Peptide dictionary: canonical name -> aliases, category, whether it is a true peptide.

Blends (e.g. "Wolverine", "Glow") map to multiple canonical peptides.
Alias patterns are regexes matched case-insensitively on word boundaries.
"""
from __future__ import annotations

import re

# category keys
GLP1 = "GLP-1 / metabolic"
HEAL = "Healing / recovery"
GH = "GH secretagogue"
COG = "Cognitive / mood"
LONG = "Longevity / mitochondrial"
SEX = "Sexual / tanning"
SKIN = "Skin / hair / cosmetic"
IMMUNE = "Immune / gut"
SLEEP = "Sleep"
HORM = "Hormonal"
ADJ = "Non-peptide adjunct"

# name: (aliases, category, is_peptide)
PEPTIDES: dict[str, tuple[list[str], str, bool]] = {
    # GLP-1 / metabolic
    "Semaglutide": ([r"semaglutide", r"\bsema\b", r"ozempic", r"wegovy", r"rybelsus"], GLP1, True),
    "Tirzepatide": ([r"tirzepatide", r"\btirz\b", r"\btirzep\b", r"mounjaro", r"zepbound"], GLP1, True),
    "Retatrutide": ([r"retatrutide", r"\breta\b", r"\bretat\b", r"triple[- ]?g\b", r"\bretatru"], GLP1, True),
    "Cagrilintide": ([r"cagrilintide", r"\bcagri\b"], GLP1, True),
    "Mazdutide": ([r"mazdutide", r"\bmazdu\b"], GLP1, True),
    "Survodutide": ([r"survodutide", r"\bsurvo\b"], GLP1, True),
    "Liraglutide": ([r"liraglutide", r"saxenda", r"victoza"], GLP1, True),
    "Amycretin": ([r"amycretin"], GLP1, True),
    "AOD-9604": ([r"aod[- ]?9604", r"\baod\b"], GLP1, True),
    "HGH Fragment 176-191": ([r"frag(?:ment)?[- ]?176", r"hgh[- ]?frag(?:ment)?\b", r"\bfrag\b"], GLP1, True),
    "MOTS-c": ([r"mots[- ]?c\b"], LONG, True),
    "Tesofensine": ([r"tesofensine", r"\btesof?\b"], ADJ, False),
    "5-Amino-1MQ": ([r"5[- ]?amino[- ]?1[- ]?mq", r"\b5a1mq\b", r"\b5[- ]?amino\b"], ADJ, False),
    "SLU-PP-332": ([r"slu[- ]?pp[- ]?332", r"\bslu\b"], ADJ, False),
    "GLP-1 (unspecified)": ([r"\bglp[- ]?1s?\b"], GLP1, True),
    # Healing / recovery
    "BPC-157": ([r"bpc[- ]?157", r"\bbpc\b", r"body protect(?:ion|ive) compound"], HEAL, True),
    "TB-500": ([r"tb[- ]?500", r"thymosin[- ]?beta[- ]?4", r"\btb4\b", r"\btb500\b"], HEAL, True),
    "GHK-Cu": ([r"ghk[- ]?cu", r"\bghk\b", r"copper peptide"], SKIN, True),
    "KPV": ([r"\bkpv\b"], IMMUNE, True),
    "LL-37": ([r"ll[- ]?37\b"], IMMUNE, True),
    "Thymosin Alpha-1": ([r"thymosin[- ]?alpha[- ]?1", r"\bta[- ]?1\b", r"thymalfasin", r"zadaxin"], IMMUNE, True),
    "Thymalin": ([r"thymalin"], IMMUNE, True),
    "Thymulin": ([r"thymulin"], IMMUNE, True),
    "PEG-MGF": ([r"peg[- ]?mgf"], HEAL, True),
    "MGF": ([r"\bmgf\b", r"mechano growth factor"], HEAL, True),
    "IGF-1 LR3": ([r"igf[- ]?1[- ]?lr3", r"\blr3\b"], HEAL, True),
    "IGF-1 DES": ([r"igf[- ]?1[- ]?des", r"\bdes[- ]?igf"], HEAL, True),
    "ARA-290": ([r"ara[- ]?290", r"cibinetide"], HEAL, True),
    "VIP": ([r"\bvip\b(?!\s*(?:lounge|member|access|ticket))", r"vasoactive intestinal"], IMMUNE, True),
    "Larazotide": ([r"larazotide"], IMMUNE, True),
    "Pentadeca Arginate": ([r"pentadeca[- ]?arginate", r"\bpda\b"], HEAL, True),
    # GH secretagogues
    "CJC-1295": ([r"cjc[- ]?1295", r"\bcjc\b", r"mod(?:ified)?[- ]?grf", r"grf[- ]?1[- ]?29"], GH, True),
    "Ipamorelin": ([r"ipamorelin", r"\bipa\b(?!\s*beer)"], GH, True),
    "Tesamorelin": ([r"tesamorelin", r"egrifta", r"\btesa\b"], GH, True),
    "Sermorelin": ([r"sermorelin", r"\bsermo\b"], GH, True),
    "GHRP-2": ([r"ghrp[- ]?2\b"], GH, True),
    "GHRP-6": ([r"ghrp[- ]?6\b"], GH, True),
    "Hexarelin": ([r"hexarelin"], GH, True),
    "MK-677": ([r"mk[- ]?677", r"ibutamoren"], ADJ, False),
    "HGH": ([r"\bhgh\b", r"somatropin", r"growth hormone(?! secretagogue| releasing| peptide)", r"\bgh\b(?!\s*(?:peptide|secretagogue|releasing))"], HORM, True),
    "IGF-1": ([r"\bigf[- ]?1\b(?![- ]?(?:lr3|des))"], HORM, True),
    # Cognitive / mood
    "Semax": ([r"\bn?a?[- ]?semax\b"], COG, True),
    "Selank": ([r"\bn?a?[- ]?selank\b"], COG, True),
    "Dihexa": ([r"dihexa"], COG, True),
    "Cerebrolysin": ([r"cerebrolysin"], COG, True),
    "P21": ([r"\bp[- ]?21\b"], COG, True),
    "Pinealon": ([r"pinealon"], COG, True),
    "Cortexin": ([r"cortexin"], COG, True),
    "Noopept": ([r"noopept"], ADJ, False),
    "Oxytocin": ([r"oxytocin"], COG, True),
    "Vasopressin": ([r"vasopressin", r"desmopressin"], COG, True),
    "DSIP": ([r"\bdsip\b", r"delta sleep[- ]inducing"], SLEEP, True),
    # Longevity / mitochondrial
    "Epitalon": ([r"epitalon", r"epithalon", r"epithalamin"], LONG, True),
    "SS-31": ([r"ss[- ]?31\b", r"elamipretide"], LONG, True),
    "Humanin": ([r"humanin"], LONG, True),
    "FOXO4-DRI": ([r"foxo4(?:[- ]?dri)?"], LONG, True),
    "NAD+": ([r"\bnad\+", r"\bnad\b(?!\s*(?:83|bank))", r"nicotinamide adenine"], ADJ, False),
    "Glutathione": ([r"glutathione"], ADJ, False),
    "Methylene Blue": ([r"methylene blue"], ADJ, False),
    "BAM15": ([r"\bbam[- ]?15\b"], ADJ, False),
    # Sexual / tanning
    "PT-141": ([r"pt[- ]?141", r"bremelanotide", r"vyleesi"], SEX, True),
    "Melanotan II": ([r"melanotan[- ]?(?:ii|2)", r"\bmt[- ]?2\b", r"\bmt[- ]?ii\b"], SEX, True),
    "Melanotan I": ([r"melanotan[- ]?(?:i|1)\b", r"\bmt[- ]?1\b", r"afamelanotide", r"scenesse"], SEX, True),
    "Kisspeptin": ([r"kisspeptin(?:[- ]?10)?", r"\bkiss[- ]?10\b"], HORM, True),
    "Gonadorelin": ([r"gonadorelin"], HORM, True),
    "HCG": ([r"\bhcg\b", r"chorionic gonadotropin", r"pregnyl"], HORM, True),
    "Triptorelin": ([r"triptorelin"], HORM, True),
    # Skin / cosmetic
    "Snap-8": ([r"snap[- ]?8\b"], SKIN, True),
    "Argireline": ([r"argireline", r"acetyl hexapeptide[- ]?[38]"], SKIN, True),
    "Matrixyl": ([r"matrixyl", r"palmitoyl pentapeptide"], SKIN, True),
    "AHK-Cu": ([r"ahk[- ]?cu"], SKIN, True),
    "PTD-DBM": ([r"ptd[- ]?dbm"], SKIN, True),
    # Muscle / other
    "Follistatin 344": ([r"follistatin(?:[- ]?344)?"], HEAL, True),
    "ACE-031": ([r"ace[- ]?031"], HEAL, True),
    "Adipotide": ([r"adipotide"], GLP1, True),
    "Cardiogen": ([r"cardiogen"], LONG, True),
    "Vilon": ([r"\bvilon\b"], LONG, True),
    "Livagen": ([r"livagen"], LONG, True),
    "Bronchogen": ([r"bronchogen"], LONG, True),
    "Testagen": ([r"testagen"], LONG, True),
    "Ovagen": ([r"\bovagen\b"], LONG, True),
    "Prostamax": ([r"prostamax"], LONG, True),
    "Insulin": ([r"\binsulin\b(?!\s*(?:resistance|sensitivity|spike|response|levels?|index|pump|needle|syringe))"], HORM, True),
    "Tesamorelin/Ipamorelin blend": ([], GH, True),  # placeholder, resolved by blends
}
# remove placeholder entries with no aliases
PEPTIDES = {k: v for k, v in PEPTIDES.items() if v[0]}

# Blend / brand names -> set of canonical peptides
BLENDS: dict[str, tuple[list[str], list[str]]] = {
    "Wolverine": ([r"wolverine(?: stack| blend| protocol)?"], ["BPC-157", "TB-500"]),
    "Glow": ([r"\bglow(?: stack| blend| protocol| 70| 50)\b", r"\bglow\b(?=.{0,40}(?:ghk|bpc|tb))"], ["GHK-Cu", "BPC-157", "TB-500"]),
    "Klow": ([r"\bklow(?: stack| blend| protocol)?\b"], ["GHK-Cu", "BPC-157", "TB-500", "KPV"]),
    "CJC/Ipa": ([r"cjc[- /+]?ipa(?:morelin)?", r"ipa(?:morelin)?[- /+]?cjc"], ["CJC-1295", "Ipamorelin"]),
    "CagriSema": ([r"cagrisema", r"cagri[- /+]?sema\b"], ["Cagrilintide", "Semaglutide"]),
    "Tesa/Ipa": ([r"tesa(?:morelin)?[- /+]?ipa(?:morelin)?\b"], ["Tesamorelin", "Ipamorelin"]),
    "BPC/TB blend": ([r"bpc[- /+]?tb[- ]?500", r"tb[- ]?500[- /+]?bpc"], ["BPC-157", "TB-500"]),
}

CATEGORY = {name: cat for name, (_, cat, _) in PEPTIDES.items()}
IS_PEPTIDE = {name: isp for name, (_, _, isp) in PEPTIDES.items()}

_COMPILED: list[tuple[str, re.Pattern]] = []
for name, (aliases, _, _) in PEPTIDES.items():
    for a in aliases:
        _COMPILED.append((name, re.compile(a, re.I)))
_BLENDS: list[tuple[str, re.Pattern, list[str]]] = []
for bname, (aliases, members) in BLENDS.items():
    for a in aliases:
        _BLENDS.append((bname, re.compile(a, re.I), members))

# dose pattern: number + unit, allowing ranges and "x/week"
DOSE_RE = re.compile(r"(?<![\w.-])(\d+(?:\.\d+)?)\s*(?:-|to|–)?\s*(\d+(?:\.\d+)?)?\s*(mcg|ug|µg|mg|iu)\b", re.I)


def find_mentions(text: str) -> tuple[dict[str, list[int]], list[str]]:
    """Return {canonical: [positions]} and list of blend names found."""
    found: dict[str, list[int]] = {}
    blends: list[str] = []
    if not text:
        return found, blends
    for name, pat in _COMPILED:
        for m in pat.finditer(text):
            found.setdefault(name, []).append(m.end())
    for bname, pat, members in _BLENDS:
        if pat.search(text):
            blends.append(bname)
            for mname in members:
                found.setdefault(mname, [])
    return found, blends


def find_doses(text: str, positions: list[int], window: int = 90) -> list[float]:
    """Doses (in mcg) appearing within `window` chars after the end of a mention."""
    out: list[float] = []
    for p in positions:
        seg = text[p : p + window]
        m = DOSE_RE.search(seg)
        if not m:
            continue
        val = float(m.group(1))
        unit = m.group(3).lower()
        if unit == "mg":
            val *= 1000
        elif unit == "iu":
            continue  # HGH/HCG units, not comparable to mcg
        if 0 < val <= 1_000_000:
            out.append(val)
    return out
