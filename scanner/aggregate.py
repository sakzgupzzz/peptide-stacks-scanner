"""Compute dashboard statistics from the extracted corpus."""
from __future__ import annotations

import time
from collections import Counter, defaultdict
from itertools import combinations
from statistics import median

from .peptides import CATEGORY, GLP1, IS_PEPTIDE

WEEK = 7 * 86400

SHORT = {
    "Semaglutide": "Sema", "Tirzepatide": "Tirz", "Retatrutide": "Reta", "Cagrilintide": "Cagri",
    "Ipamorelin": "Ipa", "Tesamorelin": "Tesa", "Sermorelin": "Sermo", "CJC-1295": "CJC",
    "Melanotan II": "MT2", "Melanotan I": "MT1", "Thymosin Alpha-1": "TA1", "GLP-1 (unspecified)": "GLP-1",
    "HGH Fragment 176-191": "Frag", "Pentadeca Arginate": "PDA", "IGF-1 LR3": "LR3", "Liraglutide": "Lira",
    "Mazdutide": "Mazdu", "Survodutide": "Survo", "Methylene Blue": "MB", "Glutathione": "GSH",
}
# community names for exact peptide sets
KNOWN_STACKS = {
    frozenset({"BPC-157", "TB-500"}): "Wolverine",
    frozenset({"BPC-157", "TB-500", "GHK-Cu"}): "Glow",
    frozenset({"BPC-157", "TB-500", "GHK-Cu", "KPV"}): "Klow",
    frozenset({"CJC-1295", "Ipamorelin"}): "CJC/Ipa",
    frozenset({"Tesamorelin", "Ipamorelin"}): "Tesa/Ipa",
    frozenset({"Cagrilintide", "Semaglutide"}): "CagriSema",
    frozenset({"Cagrilintide", "Retatrutide"}): "Reta/Cagri",
    frozenset({"Semax", "Selank"}): "Semax/Selank",
    frozenset({"Semaglutide", "Tirzepatide"}): "Sema/Tirz",
    frozenset({"Retatrutide", "Tirzepatide"}): "Reta/Tirz",
    frozenset({"BPC-157", "KPV"}): "BPC/KPV gut",
    frozenset({"Epitalon", "GHK-Cu"}): "Epi/GHK anti-aging",
    frozenset({"PT-141", "Melanotan II"}): "MT2/PT-141",
    frozenset({"HCG", "Kisspeptin"}): "HCG/Kiss",
    frozenset({"MOTS-c", "NAD+"}): "MOTS-c/NAD+",
    frozenset({"CJC-1295", "Ipamorelin", "BPC-157", "TB-500"}): "Wolverine + CJC/Ipa",
    frozenset({"Tesamorelin", "Ipamorelin", "BPC-157", "TB-500"}): "Wolverine + Tesa/Ipa",
}
CAT_SHORT = {GLP1: "GLP-1", "Healing / recovery": "Healing", "GH secretagogue": "GH", "Cognitive / mood": "Nootropic",
             "Longevity / mitochondrial": "Longevity", "Sexual / tanning": "Libido", "Skin / hair / cosmetic": "Skin",
             "Immune / gut": "Immune", "Sleep": "Sleep", "Hormonal": "Hormone", "Non-peptide adjunct": "Adjunct"}
SIZE_WORD = {2: "duo", 3: "trio", 4: "quad"}


def name_stack(peptides: list[str], observed: "Counter", goals: "Counter") -> dict:
    """Return {name, kind, named}. Community name if known/observed, else short peptide names."""
    key = frozenset(peptides)
    cats = {CATEGORY.get(p, "Other") for p in peptides}
    kind = (f"{CAT_SHORT.get(next(iter(cats)), 'Mixed')} {SIZE_WORD.get(len(peptides), 'stack')}" if len(cats) == 1
            else f"{goals.most_common(1)[0][0]} stack" if goals else "Mixed stack")
    if key in KNOWN_STACKS:
        return {"name": KNOWN_STACKS[key], "kind": kind, "named": True}
    # largest known subset + remainder
    best = max((k for k in KNOWN_STACKS if k < key), key=len, default=None)
    if best is not None:
        rest = [SHORT.get(p, p) for p in peptides if p not in best]
        tail = " + ".join(rest) if len(rest) <= 2 else f"{len(rest)} more"
        return {"name": f"{KNOWN_STACKS[best]} + {tail}", "kind": kind, "named": True}
    if observed:
        blend = observed.most_common(1)[0][0]
        return {"name": blend if len(peptides) <= 3 else f"{blend} + more", "kind": kind, "named": True}
    shorts = [SHORT.get(p, p) for p in peptides]
    name = " + ".join(shorts) if len(shorts) <= 3 else " + ".join(shorts[:2]) + f" + {len(shorts) - 2} more"
    return {"name": name, "kind": kind, "named": False}


GENERIC = {"GLP-1 (unspecified)": lambda ps: any(CATEGORY.get(p) == GLP1 and p != "GLP-1 (unspecified)" for p in ps),
           "IGF-1": lambda ps: "IGF-1 LR3" in ps or "IGF-1 DES" in ps}


def normalize(rec: dict) -> dict:
    """Drop class-level mentions when a specific member is present (idempotent, applied to old corpus rows too)."""
    ps = rec.get("peptides") or []
    drop = {g for g, cond in GENERIC.items() if g in ps and cond(ps)}
    if drop:
        rec = dict(rec, peptides=[p for p in ps if p not in drop])
    return rec


def _trend(now_ts: int, timestamps: list[int]) -> tuple[int, int]:
    """(count in last 30 days, count in prior 30 days)"""
    recent = sum(1 for t in timestamps if now_ts - t <= 30 * 86400)
    prior = sum(1 for t in timestamps if 30 * 86400 < now_ts - t <= 60 * 86400)
    return recent, prior


def aggregate(records: list[dict], now_ts: int | None = None, max_stacks: int = 150, top_n: int = 25) -> dict:
    now_ts = now_ts or int(time.time())
    records = [normalize(r) for r in records]
    records = [r for r in records if r.get("peptides")]

    # ---- per-peptide
    pep_docs: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        for p in r["peptides"]:
            pep_docs[p].append(r)

    peptides = []
    for p, docs in pep_docs.items():
        ts = [d["ts"] for d in docs]
        recent, prior = _trend(now_ts, ts)
        doses = [d["doses"][p] for d in docs if p in d.get("doses", {})]
        subs = Counter(d["sub"] for d in docs)
        co = Counter()
        for d in docs:
            for q in d["peptides"]:
                if q != p:
                    co[q] += 1
        goals = Counter(g for d in docs for g in d.get("goals", []))
        peptides.append({
            "name": p,
            "category": CATEGORY.get(p, "Other"),
            "is_peptide": IS_PEPTIDE.get(p, True),
            "docs": len(docs),
            "recent_30d": recent,
            "prior_30d": prior,
            "median_dose_mcg": round(median(doses), 1) if doses else None,
            "dose_samples": len(doses),
            "top_subs": subs.most_common(3),
            "top_partners": co.most_common(6),
            "top_goals": goals.most_common(3),
            "first_seen": min(ts) if ts else None,
            "last_seen": max(ts) if ts else None,
        })
    peptides.sort(key=lambda x: -x["docs"])

    # ---- exact stacks (>=2 distinct peptides in one doc)
    stack_docs: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        if len(r["peptides"]) >= 2:
            stack_docs[tuple(r["peptides"])].append(r)
    stacks = []
    spark_weeks = 12
    spark_start = now_ts - spark_weeks * WEEK
    for key, docs in stack_docs.items():
        ts = [d["ts"] for d in docs]
        recent, prior = _trend(now_ts, ts)
        goals = Counter(g for d in docs for g in d.get("goals", []))
        observed = Counter(b for d in docs for b in d.get("blends", []))
        naming = name_stack(list(key), observed, goals)
        stack_doses = {}
        for p in key:
            ds = [d["doses"][p] for d in docs if p in d.get("doses", {})]
            if ds:
                stack_doses[p] = {"median_mcg": round(median(ds), 1), "n": len(ds)}
        spark = [0] * spark_weeks
        for t in ts:
            if t >= spark_start:
                spark[min(spark_weeks - 1, (t - spark_start) // WEEK)] += 1
        examples, seen_titles = [], set()
        for d in sorted(docs, key=lambda d: (-d["ts"] // 86400, -d.get("score", 0))):
            tkey = (d["title"] or d["snippet"][:60]).lower()
            if tkey in seen_titles:
                continue
            seen_titles.add(tkey)
            examples.append(d)
            if len(examples) == 5:
                break
        stacks.append({
            "peptides": list(key),
            "name": naming["name"],
            "kind": naming["kind"],
            "named": naming["named"],
            "aka": [b for b, _ in observed.most_common(3)],
            "doses": stack_doses,
            "spark": spark,
            "size": len(key),
            "docs": len(docs),
            "hinted": sum(1 for d in docs if d.get("stack_hint")),
            "recent_30d": recent,
            "prior_30d": prior,
            "goals": goals.most_common(3),
            "subs": Counter(d["sub"] for d in docs).most_common(3),
            "examples": [{"url": e["url"], "title": e["title"] or e["snippet"][:80], "ts": e["ts"], "score": e.get("score", 0), "sub": e["sub"], "snippet": e["snippet"][:200]} for e in examples],
            "last_seen": max(ts),
            "all_peptides": all(IS_PEPTIDE.get(p, True) for p in key),
        })
    stacks.sort(key=lambda s: (-s["docs"], -s["hinted"], -s["last_seen"]))
    stacks = stacks[:max_stacks]

    # ---- pair co-occurrence (top N peptides)
    top_names = [p["name"] for p in peptides[:top_n]]
    idx = {n: i for i, n in enumerate(top_names)}
    pairs = Counter()
    for r in records:
        for a, b in combinations(sorted(r["peptides"]), 2):
            pairs[(a, b)] += 1
    matrix = [[0] * len(top_names) for _ in top_names]
    for (a, b), c in pairs.items():
        if a in idx and b in idx:
            matrix[idx[a]][idx[b]] = c
            matrix[idx[b]][idx[a]] = c
    top_pairs = [{"a": a, "b": b, "docs": c} for (a, b), c in pairs.most_common(40)]

    # ---- weekly timeline for top 10 peptides (last 26 weeks)
    weeks = 26
    start = now_ts - weeks * WEEK
    tl_names = top_names[:10]
    series = {n: [0] * weeks for n in tl_names}
    total = [0] * weeks
    for r in records:
        if r["ts"] < start:
            continue
        w = min(weeks - 1, (r["ts"] - start) // WEEK)
        total[w] += 1
        for p in r["peptides"]:
            if p in series:
                series[p][w] += 1
    timeline = {
        "week_starts": [start + i * WEEK for i in range(weeks)],
        "total": total,
        "series": [{"name": n, "values": v} for n, v in series.items()],
    }

    # ---- goals, subs, sources, categories
    goal_counts = Counter(g for r in records for g in r.get("goals", []))
    goal_stacks: dict[str, Counter] = defaultdict(Counter)
    for r in records:
        if len(r["peptides"]) >= 2:
            for g in r.get("goals", []):
                goal_stacks[g][tuple(r["peptides"])] += 1
    goals = [{
        "goal": g, "docs": c,
        "top_stacks": [{"peptides": list(k), "docs": n} for k, n in goal_stacks[g].most_common(5)],
    } for g, c in goal_counts.most_common()]

    sub_counts = Counter(r["sub"] for r in records).most_common(30)
    source_counts = Counter(r["source"] for r in records)
    cat_counts = Counter(CATEGORY.get(p, "Other") for r in records for p in r["peptides"])

    recent_docs = sorted([r for r in records if len(r["peptides"]) >= 2], key=lambda r: -r["ts"])[:60]

    # ---- risers: peptides with biggest 30d growth (min 5 recent docs)
    risers = sorted(
        [p for p in peptides if p["recent_30d"] >= 5],
        key=lambda p: -((p["recent_30d"] + 1) / (p["prior_30d"] + 1)),
    )[:8]

    return {
        "generated_at": now_ts,
        "totals": {
            "docs": len(records),
            "stack_docs": sum(1 for r in records if len(r["peptides"]) >= 2),
            "distinct_peptides": len(peptides),
            "distinct_stacks": len(stack_docs),
            "sources": dict(source_counts),
            "oldest": min((r["ts"] for r in records), default=None),
            "newest": max((r["ts"] for r in records), default=None),
        },
        "peptides": peptides,
        "stacks": stacks,
        "pairs": {"names": top_names, "matrix": matrix, "top": top_pairs},
        "timeline": timeline,
        "goals": goals,
        "subreddits": sub_counts,
        "categories": cat_counts.most_common(),
        "risers": [{"name": p["name"], "recent": p["recent_30d"], "prior": p["prior_30d"]} for p in risers],
        "recent": [{k: r[k] for k in ("url", "title", "sub", "source", "ts", "score", "peptides", "goals", "snippet", "blends")} for r in recent_docs],
    }
