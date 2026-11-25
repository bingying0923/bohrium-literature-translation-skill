#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成 result.json + intro.md + citation_map.csv。

用法:
    python3 make_result.py --case-json /input/case.json --intro work/intro.json \
        --check work/check.json --out /app/output/result.json
"""
import argparse
import csv
import json
import os
import sys


def load(path, default=None):
    if not path or not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-json", default=None)
    ap.add_argument("--intro", required=True)
    ap.add_argument("--check", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    case = load(args.case_json, {}) or {}
    intro = load(args.intro, {}) or {}
    check = load(args.check, {}) or {}
    paras = intro.get("paragraphs") or []
    outline = intro.get("outline") or {}

    issues = []
    for k, v in (check.get("checks") or {}).items():
        for it in v.get("issues") or []:
            issues.append({"where": it.get("where", k), "issue": it.get("issue", k),
                           "suggested_action": "按规则回改后重跑 check_intro.py"})

    result = {
        "case_id": case.get("case_id") or case.get("id") or "unknown",
        "status": "success" if check.get("ok") else "partial",
        "outline": outline,
        "intro": {"paragraphs": paras},
        "citation_map": [{"sentence_id": p.get("id"), "claims": p.get("text", "")[:80],
                           "refs": p.get("citations") or []} for p in paras],
        "checks": check.get("checks", {}),
        "issues": issues,
        "artifacts": [{"path": "intro.md", "kind": "markdown"},
                      {"path": "citation_map.csv", "kind": "csv"}],
    }
    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    titles = {"background": "1 研究背景", "related": "2 相关工作",
              "gap": "3 研究空白", "contributions": "4 本文贡献"}
    md = ["# 引言与相关工作（%s）" % result["case_id"], ""]
    for p in paras:
        md.append("## " + titles.get(p.get("role"), p.get("role", "")))
        md.append("")
        md.append(p.get("text", ""))
        md.append("")
    with open(os.path.join(out_dir, "intro.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    with open(os.path.join(out_dir, "citation_map.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sentence_id", "role", "refs", "text"])
        for p in paras:
            w.writerow([p.get("id"), p.get("role"), ";".join(map(str, p.get("citations") or [])),
                        p.get("text", "")[:120]])

    print(json.dumps({"status": "ok", "out": args.out, "case_status": result["status"],
                      "paragraphs": len(paras), "issues": len(issues)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
