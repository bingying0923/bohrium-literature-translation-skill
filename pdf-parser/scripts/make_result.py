#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成 result.json + document.md（结构树、表格、公式、图表题注、质量报告）。

用法:
    python3 make_result.py --case-json /input/case.json --blocks work/blocks.json \
        --tables work/tables.json --out /app/output/result.json
"""
import argparse
import json
import os
import re
import sys

HEAD_RE = re.compile(r"^(?:\d+(?:\.\d+)*\.?\s+)?(abstract|introduction|related work|background|"
                     r"methods?|materials and methods|results?|discussion|conclusions?|"
                     r"references|acknowledge?ments?|limitations?|appendix)\b", re.I)
CAPTION_RE = re.compile(r"^(figure|fig\.?|table|scheme)\s*\d+", re.I)
FORMULA_RE = re.compile(r"\$[^$]{1,200}\$|\bEq\.?\s*\(?\d+\)?|\\begin\{equation\}")


def load(path, default=None):
    if not path or not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-json", default=None)
    ap.add_argument("--blocks", required=True)
    ap.add_argument("--tables", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    case = load(args.case_json, {}) or {}
    bdata = load(args.blocks, {}) or {}
    doc = bdata.get("doc", {})
    pages = bdata.get("pages", [])
    tdata = load(args.tables, {}) or {}
    tables = tdata.get("tables", [])
    twarn = tdata.get("warnings", [])

    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)

    sections, figures, formulas, body = [], [], [], []
    cur = None
    for p in pages:
        for b in p["blocks"]:
            text = b["text"].strip()
            if not text:
                continue
            if CAPTION_RE.match(text):
                figures.append({"anchor": b["anchor"], "page": p["page"], "caption": text[:300]})
                cur["blocks"].append({"anchor": b["anchor"], "type": "caption", "text": text})
                continue
            if FORMULA_RE.search(text):
                formulas.append({"anchor": b["anchor"], "page": p["page"], "raw": text[:200]})
            if HEAD_RE.match(text) and len(text) < 90:
                cur = {"name": text.rstrip("."), "page": p["page"], "anchor": b["anchor"], "blocks": []}
                sections.append(cur)
                continue
            if cur is None:
                cur = {"name": "Front Matter", "page": p["page"], "anchor": b["anchor"], "blocks": []}
                sections.append(cur)
            cur["blocks"].append({"anchor": b["anchor"], "type": "text", "text": text})
            body.append(text)

    quality = {
        "pages": doc.get("pages", 0),
        "columns_detected": doc.get("columns", 1),
        "blocks": doc.get("blocks", 0),
        "sections": len(sections),
        "tables": len(tables),
        "figures": len(figures),
        "formulas": len(formulas),
        "warnings": twarn,
    }
    problems = []
    if not sections:
        problems.append("未识别到章节标题，结果退化为纯段落流")
    if twarn:
        problems.append("表格存在合并单元格/续表告警，需人工确认")
    if not formulas and "equation" in " ".join(body).lower():
        problems.append("正文提到公式但未抽取到公式块")

    result = {
        "case_id": case.get("case_id") or case.get("id") or "unknown",
        "status": "success" if not problems else "partial",
        "document": {"title": case.get("title") or doc.get("source_file", ""),
                     "pages": doc.get("pages", 0),
                     "columns": doc.get("columns", 1),
                     "source_file": doc.get("source_file", "")},
        "structure": [{"name": s["name"], "page": s["page"], "anchor": s["anchor"],
                       "blocks": len(s["blocks"])} for s in sections],
        "sections": [{"name": s["name"], "page": s["page"], "anchor": s["anchor"],
                      "blocks": s["blocks"]} for s in sections],
        "tables": tables,
        "figures": figures,
        "formulas": formulas,
        "quality": quality,
        "issues": problems,
        "artifacts": [{"path": "document.md", "kind": "markdown"}],
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    md = ["# 解析结果（%s）" % result["case_id"], "",
          "> 版式：%d 页 / %d 栏；块锚点 bNNNN 对应版面顺序。" % (doc.get("pages", 0), doc.get("columns", 1)), ""]
    for s in sections:
        md.append("## %s（第 %s 页）" % (s["name"], s["page"]))
        md.append("")
        for b in s["blocks"]:
            md.append(b["text"] if b["type"] == "text" else "> " + b["text"])
            md.append("")
    if tables:
        md.append("## 表格")
        md.append("")
        for t in tables:
            md.append("### %s（第 %s 页，%d 行 × %d 列）" % (t["id"], t["page"], t["rows"], t["cols"]))
            md.append("")
            md.append(t["markdown"])
            md.append("")
    with open(os.path.join(out_dir, "document.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(json.dumps({"status": "ok", "out": args.out, "case_status": result["status"],
                      "sections": len(sections), "tables": len(tables),
                      "figures": len(figures), "formulas": len(formulas)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())

