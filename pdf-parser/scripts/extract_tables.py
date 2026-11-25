#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从版面文本里抽表格，转成 Markdown（含合并单元格告警）。

用法:
    python3 extract_tables.py --input layout.txt --out work/tables.json

判定: 连续 ≥3 行、每行由 2+ 个"两空格以上间隙"分隔、且各列起始位置对齐（容差 2 字符）。
"""
import argparse
import json
import os
import re
import sys

PAGE_RE = re.compile(r"^\[page\s*(\d+)\]$", re.I)
SPLIT_RE = re.compile(r"\s{2,}")


def read_text(path):
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return open(path, "r", encoding=enc).read().replace("\r\n", "\n")
        except (UnicodeDecodeError, LookupError):
            continue
    return open(path, "r", encoding="utf-8", errors="ignore").read()


def split_pages(text):
    text = text.replace("\r", "\n")
    if "\f" in text:
        return [(i + 1, p.split("\n")) for i, p in enumerate(text.split("\f"))]
    pages, cur, n = [], [], 0
    for ln in text.split("\n"):
        m = PAGE_RE.match(ln.strip())
        if m:
            if cur:
                pages.append((n or len(pages) + 1, cur))
            cur, n = [], int(m.group(1))
        else:
            cur.append(ln)
    if cur:
        pages.append((n or len(pages) + 1, cur))
    return pages


def columns_of(line):
    """返回 [(start, text)]"""
    cols, pos = [], 0
    for part in SPLIT_RE.split(line.rstrip()):
        if not part.strip():
            pos += len(part)
            continue
        start = line.find(part, pos)
        cols.append((start, part.strip()))
        pos = start + len(part)
    return cols


def aligned(rows):
    if len(rows) < 2:
        return False
    starts = [[c[0] for c in r] for r in rows]
    n = min(len(s) for s in starts)
    if n < 2:
        return False
    for i in range(n):
        vals = [s[i] for s in starts if len(s) > i]
        if max(vals) - min(vals) > 3:
            return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pages = split_pages(read_text(args.input))
    tables, tid = [], 0
    warnings = []
    for no, lines in pages:
        run, run_start = [], 0
        for i, ln in enumerate(lines + [""]):
            cols = columns_of(ln) if ln.strip() else []
            if len(cols) >= 2:
                if not run:
                    run_start = i
                run.append(cols)
            else:
                if len(run) >= 3 and aligned(run):
                    tid += 1
                    ncol = min(len(r) for r in run)
                    rows = [[c[1] for c in r[:ncol]] for r in run]
                    md = ["| " + " | ".join(rows[0]) + " |",
                          "|" + "|".join(["---"] * ncol) + "|"]
                    for r in rows[1:]:
                        md.append("| " + " | ".join(r) + " |")
                    ragged = any(len(r) != ncol for r in run)
                    if ragged:
                        warnings.append({"table_id": "t%03d" % tid, "issue": "列数不一致（可能含合并单元格）",
                                         "page": no})
                    tables.append({"id": "t%03d" % tid, "page": no, "rows": len(rows),
                                   "cols": ncol, "markdown": "\n".join(md),
                                   "source_start_line": run_start + 1})
                run = []
        # 跨页续表提示
    for i in range(len(tables) - 1):
        if tables[i]["page"] != tables[i + 1]["page"]:
            warnings.append({"table_id": tables[i]["id"], "issue": "可能与下一页表格为续表，需要人工确认合并"})

    out = {"tables": tables, "warnings": warnings}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "tables": len(tables), "warnings": len(warnings)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
