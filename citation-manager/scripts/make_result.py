#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成 result.json + manuscript.md + references.json。

用法:
    python3 make_result.py --case-json /input/case.json --refs work/refs.json \
        --revised work/revised.json --audit work/audit.json --out /app/output/result.json
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
    ap.add_argument("--refs", required=True)
    ap.add_argument("--revised", required=True)
    ap.add_argument("--audit", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    case = load(args.case_json, {}) or {}
    refs = load(args.refs, {}) or {}
    rev = load(args.revised, {}) or {}
    audit = load(args.audit, {}) or {}

    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)

    entries = rev.get("entries") or refs.get("entries") or []
    body = rev.get("body") or refs.get("body") or ""
    issues = audit.get("issues", {})

    todo = []
    for n in issues.get("missing_references", []):
        todo.append({"issue": "正文引用了 [%s]，文末列表缺失" % n,
                     "suggested_action": "补该条文献，或从正文删除该引用"})
    for n in issues.get("uncited_references", []):
        todo.append({"issue": "文末第 %s 条在正文中未被引用" % n,
                     "suggested_action": "在合适论断处补引，或从列表删除"})
    for d in issues.get("duplicates", []):
        todo.append({"issue": "疑似重复条目 %s（key=%s）" % (d["indices"], d["key"]),
                     "suggested_action": "保留信息最全的一条，正文编号合并"})
    for g in issues.get("numbering_gaps", [])[:10]:
        todo.append({"issue": "编号缺号 %s" % g, "suggested_action": "按首次出现顺序重排（renumber.py）"})
    for e in issues.get("incomplete_entries", []):
        todo.append({"issue": "第 %s 条缺字段：%s" % (e["index"], ",".join(e["missing"])),
                     "suggested_action": "补全作者/年份/题名后再提交"})

    status = "success" if audit.get("ok") else "partial"
    if not entries:
        status = "failed"

    result = {
        "case_id": case.get("case_id") or case.get("id") or "unknown",
        "status": status,
        "style": refs.get("list_style", "unknown"),
        "manuscript": {"body": body,
                       "citations_in_text": len(refs.get("citations", [])),
                       "references": len(entries)},
        "references": entries,
        "audit": {
            "missing_references": issues.get("missing_references", []),
            "uncited_references": issues.get("uncited_references", []),
            "numbering_gaps": issues.get("numbering_gaps", []),
            "order_of_appearance_ok": issues.get("order_of_appearance_ok", True),
            "first_appearance_order": issues.get("first_appearance_order", []),
            "duplicates": issues.get("duplicates", []),
            "incomplete_entries": issues.get("incomplete_entries", []),
            "style_mixed": issues.get("style_mixed", {}),
        },
        "changes": {"renumber_mapping": rev.get("mapping", {}),
                    "merged_duplicates": rev.get("merged", {}),
                    "markers_updated": len(rev.get("changes", []))},
        "todo": todo,
        "artifacts": [{"path": "manuscript.md", "kind": "markdown"},
                      {"path": "references.json", "kind": "json"},
                      {"path": "citation_changes.csv", "kind": "csv"}],
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    md = [body.rstrip(), "", "## References", ""]
    for e in entries:
        md.append("[%d] %s" % (e["index"], e["raw"]))
    with open(os.path.join(out_dir, "manuscript.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    with open(os.path.join(out_dir, "references.json"), "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)

    with open(os.path.join(out_dir, "citation_changes.csv"), "w", encoding="utf-8-sig") as f:
        f.write("old,new\n")
        for k, v in sorted((rev.get("mapping") or {}).items(), key=lambda x: int(x[0])):
            f.write("%s,%s\n" % (k, v))

    print(json.dumps({"status": "ok", "out": args.out, "case_status": status,
                      "entries": len(entries), "todo": len(todo)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
