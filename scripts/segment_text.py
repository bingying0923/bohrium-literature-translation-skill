#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把论文文本切成带段号、页码、章节的段落。

用法:
    python3 segment_text.py --input work/source.txt --out work/segments.json [--lang en]

输入约定:
    - 页边界用换页符 \\f 或单行 "[page N]" 标记(可选)
    - 空行分段; 单个换行视为同段内的折行

输出:
    {"doc": {...}, "segments": [{"id","section","page","source","char_len"}...]}
"""
import argparse
import json
import os
import re
import sys

HEADINGS = [
    r"abstract", r"introduction", r"background", r"related work", r"methods?",
    r"materials and methods", r"results?", r"discussion", r"conclusions?",
    r"concluding remarks", r"acknowledge?ments?", r"references", r"bibliography",
    r"supplementary", r"appendix",
]
HEAD_RE = re.compile(r"^(?:\d+(?:\.\d+)*\.?\s+)?(" + "|".join(HEADINGS) + r")\b", re.I)
CAPTION_RE = re.compile(r"^(?:figure|fig\.?|table|scheme)\s*\d+", re.I)
PAGE_RE = re.compile(r"^\[page\s*(\d+)\]$", re.I)
NUM_HEAD_RE = re.compile(r"^\d+(?:\.\d+)*\.?\s+[A-Z][^.]{2,80}$")


def read_text(path):
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    with open(path, "rb") as f:
        return f.read().decode("utf-8", "ignore")


def split_pages(text):
    """返回 [(page_no, text)]"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "\f" in text:
        parts = text.split("\f")
        return [(i + 1, p) for i, p in enumerate(parts)]
    pages, cur, no = [], [], 0
    for line in text.split("\n"):
        m = PAGE_RE.match(line.strip())
        if m:
            if cur:
                pages.append((no or len(pages) + 1, "\n".join(cur)))
            cur, no = [], int(m.group(1))
        else:
            cur.append(line)
    if cur:
        pages.append((no or len(pages) + 1, "\n".join(cur)))
    return pages or [(1, text)]


def blocks(page_text):
    """按空行切块, 块内折行合并成一行。"""
    out, buf = [], []
    for line in page_text.split("\n"):
        s = line.strip()
        if not s:
            if buf:
                out.append(" ".join(buf))
                buf = []
            continue
        if s.startswith("---") or re.match(r"^\d{1,3}$", s):  # 页码行/分隔线
            continue
        buf.append(s)
    if buf:
        out.append(" ".join(buf))
    return out


def classify(text, section):
    t = text.strip()
    if HEAD_RE.match(t) and len(t) < 90:
        return "heading", HEAD_RE.match(t).group(1).title()
    if NUM_HEAD_RE.match(t) and len(t) < 90:
        return "heading", section
    if CAPTION_RE.match(t):
        return "caption", "Caption"
    return "body", section


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lang", default="en")
    ap.add_argument("--min-len", type=int, default=2, help="短于此长度的块丢弃")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(json.dumps({"status": "failed", "reason": "input not found: " + args.input},
                         ensure_ascii=False))
        return 2

    raw = read_text(args.input)
    pages = split_pages(raw)
    segs, section, idx = [], "Front Matter", 0
    for page_no, ptxt in pages:
        for blk in blocks(ptxt):
            if len(blk) < args.min_len:
                continue
            kind, section = classify(blk, section)
            idx += 1
            segs.append({
                "id": "p%03d" % idx,
                "section": "References" if section.lower().startswith("reference") else section,
                "page": page_no,
                "kind": kind,
                "source": blk,
                "char_len": len(blk),
            })

    doc = {
        "source_file": os.path.basename(args.input),
        "pages": len(pages),
        "segments": len(segs),
        "chars": sum(s["char_len"] for s in segs),
        "lang": args.lang,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"doc": doc, "segments": segs}, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "out": args.out, "doc": doc}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
