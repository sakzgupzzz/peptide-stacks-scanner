"""Turn raw docs into compact records with extracted peptides, doses, goals."""
from __future__ import annotations

import re
from statistics import median

from .peptides import CATEGORY, GLP1 as GLP1_CAT, find_doses, find_mentions

GOALS: dict[str, list[str]] = {
    "Fat loss": [r"fat loss", r"weight loss", r"lose (?:weight|fat)", r"cutting", r"\bcut\b", r"appetite", r"lbs? (?:down|lost)", r"obesity", r"body ?comp"],
    "Injury / healing": [r"injur", r"tendon", r"ligament", r"tear\b", r"surgery", r"heal", r"recover", r"joint", r"\bpain\b", r"inflamm", r"rotator", r"knee", r"shoulder", r"\bback pain", r"gut"],
    "Muscle / performance": [r"muscle", r"hypertrophy", r"bulk", r"strength", r"\bgains?\b", r"lean mass", r"athlet", r"performance", r"\bpr\b"],
    "Anti-aging / longevity": [r"anti[- ]?aging", r"longevity", r"lifespan", r"telomere", r"aging", r"mitochond", r"senescen"],
    "Cognitive / mood": [r"focus", r"anxiety", r"depress", r"cognit", r"memory", r"\bmood\b", r"brain fog", r"nootropic", r"adhd", r"motivation"],
    "Sleep": [r"\bsleep", r"insomnia", r"circadian", r"deep sleep", r"rem\b"],
    "Skin / hair": [r"\bskin\b", r"wrinkle", r"collagen", r"\bhair\b", r"cosmetic", r"tanning", r"\btan\b", r"glow"],
    "Sexual / libido": [r"libido", r"erecti", r"\bsex\b", r"sexual", r"arousal", r"\bed\b"],
    "Immune / gut": [r"immune", r"autoimmune", r"\bibs\b", r"\bibd\b", r"crohn", r"colitis", r"leaky gut", r"long covid", r"infection", r"lyme"],
    "Hormone / TRT": [r"\btrt\b", r"testosterone", r"fertility", r"\bhpta\b", r"post[- ]?cycle", r"\bpct\b"],
}
_GOALS = {g: [re.compile(p, re.I) for p in pats] for g, pats in GOALS.items()}

STACK_HINT = re.compile(r"\bstack|\bprotocol|\bcycle\b|\bregimen|\bcombo|\btogether|\balongside|\bcurrently (?:on|taking|running)|\bmy (?:current )?(?:stack|protocol)|\brunning\b", re.I)


def classify_goals(text: str) -> list[str]:
    return [g for g, pats in _GOALS.items() if any(p.search(text) for p in pats)]


def extract(doc: dict) -> dict | None:
    text = f"{doc.get('title','')}\n{doc.get('text','')}"
    if len(text) < 8:
        return None
    mentions, blends = find_mentions(text)
    if not mentions:
        return None
    doses = {}
    for name, positions in mentions.items():
        ds = find_doses(text, positions)
        if ds:
            doses[name] = round(median(ds), 1)
    # generic class mentions add no stack information when a specific member is present
    if "GLP-1 (unspecified)" in mentions and any(CATEGORY.get(n) == GLP1_CAT and n != "GLP-1 (unspecified)" for n in mentions):
        mentions.pop("GLP-1 (unspecified)")
    if "IGF-1" in mentions and any(n in mentions for n in ("IGF-1 LR3", "IGF-1 DES")):
        mentions.pop("IGF-1")
    peptides = sorted(mentions)
    snippet = re.sub(r"\s+", " ", doc.get("text", "") or doc.get("title", "")).strip()[:280]
    return {
        "id": doc["id"],
        "source": doc["source"],
        "sub": doc.get("subreddit", ""),
        "url": doc.get("url", ""),
        "title": (doc.get("title") or "")[:160],
        "ts": int(doc.get("created_utc") or 0),
        "score": int(doc.get("score") or 0),
        "peptides": peptides,
        "blends": blends,
        "doses": doses,
        "goals": classify_goals(text),
        "stack_hint": bool(STACK_HINT.search(text)),
        "snippet": snippet,
    }
