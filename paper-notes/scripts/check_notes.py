#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核查笔记质量：覆盖度 / 锚点有效性 / 数字溯源 / 新增事实 / 局限字段。

用法:
    python3 check_notes.py --sections work/sections.json --notes work/notes.json \
        --card work/card.json --out work/check.json
"""
import argparse
import json
import os
import re
import sys

NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
CAUSAL = re.compile(r"\b(because|therefore|thus|lead(?:s|ing)? to|result(?:s)? in|caus(?:e|es|ed)|"
                    r"due to|as a result|因此|导致|由于|所以)\b", re.I)
SKIP_SECTIONS = {"References", "Acknowledgments", "Front Matter"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sections", required=True)
    ap.add_argument("--notes", required=True)
    ap.add_argument("--card", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.sections, "r", encoding="utf-8") as f:
        sections = json.load(f).get("sections", [])
    with open(args.notes, "r", encoding="utf-8-sig") as f:
        notes = json.load(f).get("notes", [])
    with open(args.card, "r", encoding="utf-8-sig") as f:
        card = json.load(f)

    anchors = {}
    for sec in sections:
        for para in sec["paragraphs"]:
            anchors[para["anchor"]] = {"section": sec["name"], "page": para["page"], "text": para["text"]}

    issues = {"anchors": [], "numbers": [], "no_new_facts": [], "limitations": []}

    for n in notes:
        a = n.get("anchor", "")
        if a not in anchors:
            issues["anchors"].append({"anchor": a, "issue": "锚点不存在", "note": n.get("text", "")[:80]})
            continue
        src = anchors[a]["text"]
        for num in NUM_RE.findall(n.get("text", "")):
            if num not in src:
                issues["numbers"].append({"anchor": a, "number": num, "note": n.get("text", "")[:80]})
        if CAUSAL.search(n.get("text", "")) and not CAUSAL.search(src):
            issues["no_new_facts"].append({"anchor": a, "issue": "笔记新增因果表述",
                                           "note": n.get("text", "")[:80]})

    covered = {n.get("section") for n in notes}
    target_sections = [s["name"] for s in sections
                       if s["name"] not in SKIP_SECTIONS and s["paragraphs"]]
    missing = [s for s in target_sections if s not in covered]

    lim = card.get("limitations", {})
    lim_ok = lim.get("status") == "reported"
    paper_has_lim_section = "Limitations" in target_sections
    if paper_has_lim_section and not lim_ok:
        issues["limitations"].append({"issue": "原文有限制章节但未抽取到限制字段"})
    if not paper_has_lim_section and not lim_ok:
        issues["limitations"].append({"issue": "原文未单列限制章节，limitations 标 not_reported（可接受）",
                                      "severity": "info"})

    blocking = sum(len(v) for k, v in issues.items() if k != "limitations")
    infos = [i for i in issues["limitations"] if i.get("severity") == "info"]
    real_lim = [i for i in issues["limitations"] if i.get("severity") != "info"]

    check = {
        "coverage": {"sections_total": len(target_sections), "sections_covered": len(target_sections) - len(missing),
                     "missing": missing, "ok": not missing},
        "anchors": {"ok": not issues["anchors"], "issues": issues["anchors"]},
        "numbers": {"ok": not issues["numbers"], "issues": issues["numbers"]},
        "no_new_facts": {"ok": not issues["no_new_facts"], "issues": issues["no_new_facts"]},
        "limitations": {"ok": not real_lim, "issues": issues["limitations"]},
        "blocking": blocking + len(missing) + len(real_lim),
        "ok": (blocking + len(missing) + len(real_lim)) == 0,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(check, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "blocking": check["blocking"], "missing": len(missing),
                      "anchors_ok": check["anchors"]["ok"], "numbers_ok": check["numbers"]["ok"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
