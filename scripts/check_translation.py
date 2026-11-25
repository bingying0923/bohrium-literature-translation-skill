#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核验译文: 数字/单位/引用/公式/图表编号/否定/术语一致性。

用法:
    python3 check_translation.py --segments work/segments.json \
        --translations work/translations.json --glossary work/glossary.csv \
        --out work/checks.json [--fail-ratio 0.02]

translations.json: {"p001": "第一段译文", ...}
"""
import argparse
import csv
import json
import os
import re
import sys

NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
CITE_RE = re.compile(r"\[\s*\d+(?:\s*[-–,]\s*\d+)*\s*\]")
PAREN_CITE_RE = re.compile(r"\([A-Z][A-Za-z\-']+(?:\s+et\s+al\.?)?,?\s*(?:19|20)\d{2}[a-z]?\)")
UNIT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(mg|µg|ng|kg|g|mL|µL|L|mm|cm|km|m|nm|µm|ms|s|min|h|d|"
                     r"°C|℃|K|Pa|kPa|MPa|GPa|%|ppm|ppb|M|mM|µM|nM|Hz|kHz|MHz|"
                     r"V|mV|mA|A|W|kW|J|kJ|kcal|mol|mmol|rpm|Da|kDa)\b")
FIG_RE = re.compile(r"(?:Fig(?:ure)?\.?|Table|Scheme|Eq(?:uation)?\.?)\s*\(?(\d+)\)?", re.I)
FORMULA_RE = re.compile(r"\$[^$]{1,120}\$|\\\([^)]{1,120}\\\)")
NEG_EN = re.compile(r"\b(?:not|no|none|never|neither|nor|fail(?:ed|s)?\s+to|"
                    r"absent|lack(?:s|ed)?|without|cannot|can't|isn't|aren't|wasn't|weren't|"
                    r"doesn't|don't|didn't)\b", re.I)
NEG_ZH = re.compile(r"(?:无法|未能|未|没有|没|缺乏|不存在|不需要|不具|不含|不是|并未|"
                    r"非|不(?:能|需|会|再|得|同|仅|是|具|存))")
UNIT_ZH = {"分钟": "min", "小时": "h", "天": "d", "秒": "s", "摄氏度": "°C"}


def load_glossary(path):
    rows = []
    if not path or not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            t = (r.get("term") or "").strip()
            tr = (r.get("translation") or "").strip()
            if t and tr:
                rows.append({"term": t, "translation": tr,
                             "locked": str(r.get("locked", "")).lower() in ("1", "true", "yes")})
    return rows


def spread(nums):
    out = set()
    for n in nums:
        out.add(n.replace(",", ""))
    return out


def check_segment(seg, tr, gloss):
    src, issues = seg.get("source", ""), []
    sid = seg.get("id")
    res = {}
    tr_units = tr
    for zh, en in UNIT_ZH.items():
        tr_units = tr_units.replace(zh, en)
    tr_flat = re.sub(r"\s+", "", tr)

    s_num, t_num = spread(NUM_RE.findall(src)), spread(NUM_RE.findall(tr))
    miss = sorted(s_num - t_num)
    res["numbers"] = {"ok": not miss, "issues": [{"segment_id": sid, "missing": miss}] if miss else []}

    s_unit = {m.group(2) for m in UNIT_RE.finditer(src)}
    t_unit = {m.group(2) for m in UNIT_RE.finditer(tr_units)}
    umiss = sorted(s_unit - t_unit)
    res["units"] = {"ok": not umiss, "issues": [{"segment_id": sid, "missing": umiss}] if umiss else []}

    s_cite = set(CITE_RE.findall(src)) | set(PAREN_CITE_RE.findall(src))
    t_cite = set(CITE_RE.findall(tr)) | set(PAREN_CITE_RE.findall(tr))
    cmiss = sorted(s_cite - t_cite)
    res["citations"] = {"ok": not cmiss, "issues": [{"segment_id": sid, "missing": cmiss}] if cmiss else []}

    s_f = set(FORMULA_RE.findall(src))
    t_f = set(FORMULA_RE.findall(tr)) | {x.replace(" ", "") for x in FORMULA_RE.findall(tr)}
    fmiss = sorted(x for x in s_f if x not in t_f and x.replace(" ", "") not in t_f)
    res["formulas"] = {"ok": not fmiss, "issues": [{"segment_id": sid, "missing": fmiss}] if fmiss else []}

    s_fig = {}
    for m in FIG_RE.finditer(src):
        s_fig.setdefault(m.group(1), m.group(0).strip())
    fig_issues = []
    for num, label in s_fig.items():
        is_table = label.lower().startswith("table")
        want = ("表" if is_table else "图") + num
        alt = ("Table" if is_table else "Fig") + " " + num
        if want not in tr_flat and alt.lower() not in tr_flat.lower():
            fig_issues.append({"segment_id": sid, "label": label, "expect": want})
    res["figures_tables"] = {"ok": not fig_issues, "issues": fig_issues}

    s_neg, t_neg = bool(NEG_EN.search(src)), bool(NEG_ZH.search(tr))
    neg_issues = []
    if s_neg and not t_neg:
        neg_issues.append({"segment_id": sid, "issue": "原文有否定, 译文未体现"})
    if t_neg and not s_neg and not NEG_EN.search(src):
        neg_issues.append({"segment_id": sid, "issue": "译文有否定, 原文未见"})
    res["negation"] = {"ok": not neg_issues, "issues": neg_issues}

    hits = []
    for g in gloss:
        if g["term"].lower() in src.lower():
            hits.append({"term": g["term"], "expect": g["translation"],
                         "ok": g["translation"] in tr})
    res["_terms"] = hits
    return res


def merge(parts, key):
    issues, ok = [], True
    for p in parts:
        if not p.get(key, {}).get("ok", True):
            ok = False
            issues.extend(p[key].get("issues", []))
    return {"ok": ok, "issues": issues}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--segments", required=True)
    ap.add_argument("--translations", required=True)
    ap.add_argument("--glossary", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.segments, "r", encoding="utf-8") as f:
        segs = json.load(f).get("segments", [])
    with open(args.translations, "r", encoding="utf-8") as f:
        trans = json.load(f)
    gloss = load_glossary(args.glossary)

    parts, violations, total_hits, ok_hits = [], [], 0, 0
    missing_translation = []
    for seg in segs:
        sid = seg["id"]
        if seg.get("section") == "References":
            continue
        tr = trans.get(sid)
        if not tr:
            missing_translation.append(sid)
            continue
        part = check_segment(seg, tr, gloss)
        for h in part.pop("_terms", []):
            total_hits += 1
            if h["ok"]:
                ok_hits += 1
            else:
                violations.append({"segment_id": sid, "term": h["term"], "expect": h["expect"]})
        parts.append(part)

    out = {k: merge(parts, k) for k in ("numbers", "units", "citations", "formulas",
                                        "figures_tables", "negation")}
    rate = round(ok_hits / total_hits, 4) if total_hits else 1.0
    out["term_consistency"] = {"rate": rate, "violations": violations}
    out["coverage"] = {"segments_total": len(segs),
                       "segments_translated": len(segs) - len(missing_translation),
                       "missing": missing_translation}

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "out": args.out,
                      "term_rate": rate,
                      "coverage": out["coverage"],
                      "numbers_ok": out["numbers"]["ok"],
                      "units_ok": out["units"]["ok"]}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())

