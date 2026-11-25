#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成 result.json + polished.md + changes.csv（逐句 diff 与修改类型）。

用法:
    python3 make_result.py --case-json /input/case.json --units work/units.json \
        --revised work/revised.json --terms work/terms.csv --audit work/audit.json \
        --out /app/output/result.json
"""
import argparse
import csv
import difflib
import json
import os
import re
import sys


def load_json(path, default=None):
    if not path or not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_terms(path):
    rows = []
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if (r.get("term") or "").strip():
                    rows.append({"term": r["term"].strip(),
                                 "preferred": (r.get("preferred") or "").strip(),
                                 "locked": str(r.get("locked", "")).lower() in ("1", "true", "yes"),
                                 "occurrences": [r.get("first_unit", "")]})
    return rows


def change_type(src, dst, terms):
    if src == dst:
        return ["no_change"], ["未改动"]
    types, reasons = [], []
    if re.sub(r"\s+", "", src).lower() == re.sub(r"\s+", "", dst).lower():
        types.append("format")
        reasons.append("仅大小写/空格/标点差异")
    for t in terms:
        if t["term"] and t["preferred"] and re.search(re.escape(t["term"]), src, re.I) \
                and re.search(re.escape(t["preferred"]), dst) and t["term"].lower() != t["preferred"].lower():
            types.append("terminology")
            reasons.append("按术语表统一为「%s」" % t["preferred"])
            break
    sm = difflib.SequenceMatcher(None, src.split(), dst.split())
    if not types:
        ratio = sm.ratio()
        if ratio > 0.75:
            types.append("grammar")
            reasons.append("局部语法/搭配/标点修正，句意与信息结构未变")
        elif ratio > 0.45:
            types.append("clarity")
            reasons.append("长句切分或冗余名词化拆解，信息项未增减")
        else:
            types.append("structure")
            reasons.append("句式重组（需人工确认主张强度未变）")
    return types, reasons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-json", default=None)
    ap.add_argument("--units", required=True)
    ap.add_argument("--revised", required=True)
    ap.add_argument("--terms", default=None)
    ap.add_argument("--audit", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    case = load_json(args.case_json, {}) or {}
    data = load_json(args.units, {}) or {}
    units = data.get("units", [])
    doc = data.get("doc", {})
    rev = load_json(args.revised, {}) or {}
    audit = load_json(args.audit, {}) or {}
    terms = load_terms(args.terms)

    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)

    result_units, changes = [], []
    for u in units:
        src = u.get("original", "")
        dst = rev.get(u["id"], src)
        types, reasons = change_type(src, dst, terms)
        changed = src != dst
        result_units.append({
            "id": u["id"], "paragraph": u.get("paragraph", 0),
            "original": src, "revised": dst, "changed": changed,
            "change_types": types, "reasons": reasons,
            "protected": u.get("protected", {}),
        })
        changes.append({"unit_id": u["id"], "original": src, "revised": dst,
                        "change_type": ";".join(types), "reason": ";".join(reasons),
                        "risk": "high" if "structure" in types else ("none" if not changed else "low")})

    blocking = audit.get("blocking_count", 0)
    missing = len(audit.get("missing_units") or [])
    status = "success" if (blocking == 0 and missing == 0) else "partial"

    unresolved = []
    for k, items in (audit.get("blocking") or {}).items():
        for it in items:
            unresolved.append({"unit_id": it.get("unit_id", ""), "issue": k + ": " + str(it.get("issue") or it.get("missing") or ""),
                               "why": "自动核查判为必须回改", "suggested_action": "回改该句后重跑 audit_edits.py"})
    for uid in (audit.get("missing_units") or []):
        unresolved.append({"unit_id": uid, "issue": "未提供改文", "why": "超预算或解析失败",
                           "suggested_action": "补该句改文或标记 no_change"})

    result = {
        "case_id": case.get("case_id") or case.get("id") or "unknown",
        "status": status,
        "genre": case.get("genre", "journal-article"),
        "summary": {
            "units_total": len(units),
            "units_changed": sum(1 for c in changes if c["change_type"] != "no_change"),
            "blocking": blocking,
            "warnings": audit.get("warning_count", 0),
            "term_consistency": audit.get("term_consistency", {}).get("rate", 1.0),
            "hedge_preserved": audit.get("hedging", {}).get("preserved", True),
        },
        "glossary": terms,
        "units": result_units,
        "audit": {
            "numbers": {"ok": not (audit.get("blocking") or {}).get("numbers"), "blocking": (audit.get("blocking") or {}).get("numbers", [])},
            "units": {"ok": not (audit.get("blocking") or {}).get("units"), "blocking": (audit.get("blocking") or {}).get("units", [])},
            "citations": {"ok": not (audit.get("blocking") or {}).get("citations"), "blocking": (audit.get("blocking") or {}).get("citations", [])},
            "figures": {"ok": not (audit.get("blocking") or {}).get("figures"), "blocking": (audit.get("blocking") or {}).get("figures", [])},
            "negation": {"ok": not (audit.get("blocking") or {}).get("negation"), "blocking": (audit.get("blocking") or {}).get("negation", [])},
            "hedging": {"ok": audit.get("hedging", {}).get("preserved", True),
                        "blocking": (audit.get("blocking") or {}).get("hedging", []),
                        "original_count": audit.get("hedging", {}).get("original", 0),
                        "revised_count": audit.get("hedging", {}).get("revised", 0)},
            "terminology": {"ok": not (audit.get("blocking") or {}).get("terminology"),
                            "violations": (audit.get("blocking") or {}).get("terminology", [])},
        },
        "unresolved": unresolved,
        "artifacts": [{"path": "polished.md", "kind": "markdown"},
                      {"path": "changes.csv", "kind": "csv"}],
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    # polished.md：按段落聚合
    paras = {}
    for u in result_units:
        paras.setdefault(u["paragraph"], []).append(u["revised"])
    md = ["# 润色稿（%s）" % result["case_id"], "",
          "> 逐句修改记录见 changes.csv；未改动句子标 no_change。", ""]
    for p in sorted(paras):
        md.append("## 段落 %d" % p)
        md.append("")
        md.append(" ".join(paras[p]))
        md.append("")
    with open(os.path.join(out_dir, "polished.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    with open(os.path.join(out_dir, "changes.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["unit_id", "original", "revised", "change_type", "reason", "risk"])
        w.writeheader()
        for c in changes:
            w.writerow(c)

    print(json.dumps({"status": "ok", "out": args.out, "case_status": status,
                      "units": len(units), "blocking": blocking,
                      "changed": result["summary"]["units_changed"]}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
