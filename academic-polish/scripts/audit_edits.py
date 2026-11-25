#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐句核查润色是否"改坏"：数字/单位/引用/图表/否定/限定强度/术语一致性。

用法:
    python3 audit_edits.py --units work/units.json --revised work/revised.json \
        --terms work/terms.csv --out work/audit.json

revised.json: {"p01.s01": "改后的句子", ...}
输出两级：blocking（必须回改）/ warning（需人工确认）
"""
import argparse
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from segment_sentences import features, HEDGE_WORDS  # noqa: E402

STRONG = {"demonstrate", "demonstrates", "demonstrated", "prove", "proves", "proved",
          "confirm", "confirms", "confirmed", "establish", "establishes", "show",
          "shows", "showed", "conclusively", "definitively", "clearly"}


def load_terms(path):
    out = []
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if (r.get("preferred") or "").strip():
                    out.append({"term": r["term"].strip(), "preferred": r["preferred"].strip(),
                                "locked": str(r.get("locked", "")).lower() in ("1", "true", "yes")})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", required=True)
    ap.add_argument("--revised", required=True)
    ap.add_argument("--terms", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.units, "r", encoding="utf-8") as f:
        units = json.load(f).get("units", [])
    with open(args.revised, "r", encoding="utf-8-sig") as f:
        rev = json.load(f)
    terms = load_terms(args.terms)

    blocking = {"numbers": [], "units": [], "citations": [], "figures": [],
                "negation": [], "hedging": [], "terminology": []}
    warnings = {"numbers": [], "units": [], "citations": [], "figures": [],
                "negation": [], "hedging": [], "terminology": []}
    missing = []
    hedge_o = hedge_r = 0
    term_hits = term_ok = 0

    for u in units:
        uid = u["id"]
        if uid not in rev:
            missing.append(uid)
            continue
        src, dst = u.get("original", ""), rev[uid]
        fo, fr = u.get("protected") or features(src), features(dst)

        for key in ("numbers", "units", "citations", "figures"):
            miss = [x for x in fo.get(key, []) if x not in fr.get(key, [])]
            if miss:
                blocking[key].append({"unit_id": uid, "missing": miss, "src": src, "dst": dst})

        if fo.get("negation") and not fr.get("negation"):
            blocking["negation"].append({"unit_id": uid, "issue": "原文否定在改文中消失", "src": src, "dst": dst})
        elif fr.get("negation") and not fo.get("negation"):
            warnings["negation"].append({"unit_id": uid, "issue": "改文新增否定", "src": src, "dst": dst})

        ho = [w for w in HEDGE_WORDS if re.search(r"\b" + re.escape(w) + r"\b", src, re.I)]
        hr = [w for w in HEDGE_WORDS if re.search(r"\b" + re.escape(w) + r"\b", dst, re.I)]
        hedge_o += len([1 for _ in ho])
        hedge_r += len([1 for _ in hr])
        if ho and not hr:
            blocking["hedging"].append({"unit_id": uid, "issue": "限定词全部消失", "original": ho, "src": src, "dst": dst})
        elif len(hr) < len(ho):
            warnings["hedging"].append({"unit_id": uid, "issue": "限定词减少", "original": ho, "revised": hr})
        elif len(hr) > len(ho):
            warnings["hedging"].append({"unit_id": uid, "issue": "限定词增加", "original": ho, "revised": hr})

        added_strong = [w for w in STRONG if re.search(r"\b" + w + r"\b", dst, re.I)
                        and not re.search(r"\b" + w + r"\b", src, re.I)]
        if added_strong:
            blocking["hedging"].append({"unit_id": uid, "issue": "出现更强断言", "words": added_strong, "src": src, "dst": dst})

        for t in terms:
            if re.search(re.escape(t["term"]), src, re.I):
                term_hits += 1
                if re.search(re.escape(t["preferred"]), dst):
                    term_ok += 1
                else:
                    blocking["terminology"].append({"unit_id": uid, "term": t["term"],
                                                    "preferred": t["preferred"], "dst": dst})

    rate = round(term_ok / term_hits, 4) if term_hits else 1.0
    audit = {
        "units_total": len(units),
        "units_revised": len(units) - len(missing),
        "missing_units": missing,
        "blocking": {k: v for k, v in blocking.items() if v},
        "warnings": {k: v for k, v in warnings.items() if v},
        "blocking_count": sum(len(v) for v in blocking.values()),
        "warning_count": sum(len(v) for v in warnings.values()),
        "hedging": {"original": hedge_o, "revised": hedge_r, "preserved": hedge_o == hedge_r},
        "term_consistency": {"rate": rate, "hits": term_hits},
        "ok": sum(len(v) for v in blocking.values()) == 0 and not missing,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "blocking": audit["blocking_count"],
                      "warnings": audit["warning_count"], "missing": len(missing),
                      "hedge": [hedge_o, hedge_r], "term_rate": rate}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
