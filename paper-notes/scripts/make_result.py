#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成 result.json + notes.md + paper_card.json。

用法:
    python3 make_result.py --case-json /input/case.json --sections work/sections.json \
        --notes work/notes.json --card work/card.json --check work/check.json \
        --out /app/output/result.json
"""
import argparse
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
    ap.add_argument("--sections", required=True)
    ap.add_argument("--notes", required=True)
    ap.add_argument("--card", required=True)
    ap.add_argument("--check", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    case = load(args.case_json, {}) or {}
    secdata = load(args.sections, {}) or {}
    sections = secdata.get("sections", [])
    doc = secdata.get("doc", {})
    notes = (load(args.notes, {}) or {}).get("notes", [])
    card = load(args.card, {}) or {}
    check = load(args.check, {}) or {}

    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)

    status = "success" if check.get("ok") else "partial"
    if not notes:
        status = "failed"

    unresolved = []
    if check.get("coverage", {}).get("missing"):
        unresolved.append({"anchor": "", "issue": "章节未覆盖",
                           "why": "以下章节没有笔记：" + ", ".join(check["coverage"]["missing"]),
                           "suggested_action": "为这些章节各补 1~2 条带锚点的笔记"})
    for k in ("anchors", "numbers", "no_new_facts"):
        for it in (check.get(k) or {}).get("issues", []):
            unresolved.append({"anchor": it.get("anchor", ""), "issue": k,
                               "why": str(it)[:160], "suggested_action": "回到原文核对后修订笔记"})

    result = {
        "case_id": case.get("case_id") or case.get("id") or "unknown",
        "status": status,
        "paper": {"title": case.get("title") or doc.get("source_file", ""),
                  "pages": doc.get("pages", 0),
                  "sections": [s["name"] for s in sections]},
        "card": card,
        "notes": notes,
        "coverage": check.get("coverage", {}),
        "checks": {k: check.get(k, {"ok": True, "issues": []})
                   for k in ("anchors", "numbers", "no_new_facts", "limitations")},
        "unresolved": unresolved,
        "artifacts": [{"path": "notes.md", "kind": "markdown"},
                      {"path": "paper_card.json", "kind": "json"}],
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    # notes.md
    by_sec = {}
    for n in notes:
        by_sec.setdefault(n.get("section", "Other"), []).append(n)
    md = ["# 结构化笔记（%s）" % result["case_id"], "",
          "> 锚点格式 `pNNN` = 段落号，对应原文段落；页号见各行括号。", ""]
    for sec in [s["name"] for s in sections] + [k for k in by_sec if k not in [s["name"] for s in sections]]:
        if sec not in by_sec:
            continue
        md.append("## %s" % sec)
        md.append("")
        for n in by_sec[sec]:
            md.append("- [%s] %s（%s, 第 %s 页）" % (n.get("kind", "note"), n.get("text", ""),
                                                 n.get("anchor", ""), n.get("page", "?")))
        md.append("")
    md.append("## 论文卡片")
    md.append("")
    for key in ("research_question", "data", "methods", "limitations", "novelty"):
        f = card.get(key) or {}
        val = f.get("value") or "（未报告）"
        md.append("- **%s**：%s  \n  锚点：%s" % (key, val, ", ".join(f.get("anchors") or []) or "—"))
    if card.get("key_findings"):
        md.append("- **key_findings**：")
        for f in card["key_findings"]:
            if f.get("value"):
                md.append("  - %s（锚点：%s）" % (f["value"], ", ".join(f.get("anchors") or [])))
    with open(os.path.join(out_dir, "notes.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    with open(os.path.join(out_dir, "paper_card.json"), "w", encoding="utf-8") as f:
        json.dump(card, f, ensure_ascii=False, indent=1)

    print(json.dumps({"status": "ok", "out": args.out, "case_status": status,
                      "notes": len(notes), "blocking": check.get("blocking", 0)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
