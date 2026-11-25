#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""章节切分 + 段落锚点。

用法:
    python3 segment_sections.py --input input.md --out work/sections.json

输出:
    {"doc": {...}, "sections": [{"name","start_page","paragraphs":[{"anchor","page","text","sentences":[...]}]}]}
"""
import argparse
import json
import os
import re
import sys

HEADINGS = [
    ("Abstract", r"^abstract\b"),
    ("Introduction", r"^(\d+\.?\s*)?(introduction|background)\b"),
    ("Related Work", r"^(\d+\.?\s*)?(related work|literature review)\b"),
    ("Methods", r"^(\d+\.?\s*)?(methods?|materials and methods|methodology|experimental)\b"),
    ("Results", r"^(\d+\.?\s*)?(results?|findings)\b"),
    ("Discussion", r"^(\d+\.?\s*)?(discussion)\b"),
    ("Conclusion", r"^(\d+\.?\s*)?(conclusions?|concluding remarks)\b"),
    ("Limitations", r"^(\d+\.?\s*)?(limitations?|caveats?)\b"),
    ("References", r"^(\d+\.?\s*)?(references|bibliography)\b"),
    ("Acknowledgments", r"^(\d+\.?\s*)?(acknowledge?ments?)\b"),
]
PAGE_RE = re.compile(r"^\[page\s*(\d+)\]$", re.I)
SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z][a-z])")


def read_text(path):
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read().replace("\r\n", "\n")
        except (UnicodeDecodeError, LookupError):
            continue
    return open(path, "r", encoding="utf-8", errors="ignore").read()


def match_heading(line):
    s = line.strip()
    if len(s) > 80:
        return None
    for name, pat in HEADINGS:
        if re.match(pat, s, re.I):
            return name
    return None


def split_sentences(text):
    parts = SENT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    raw = read_text(args.input)
    lines = raw.split("\n")

    page = 1
    body_lines = []
    for ln in lines:
        m = PAGE_RE.match(ln.strip())
        if m:
            body_lines.append(("PAGE", int(m.group(1))))
        elif ln.strip().startswith("\f"):
            page += 1
        else:
            body_lines.append(("TEXT", ln))

    sections, cur_name, cur_paras, cur_buf, start_page = [], "Front Matter", [], [], 1
    page = 1
    counter = 0

    def flush_para():
        nonlocal cur_buf, counter
        if not cur_buf:
            return
        text = " ".join(x.strip() for x in cur_buf if x.strip())
        cur_buf = []
        if len(text) < 2:
            return
        counter += 1
        cur_paras.append({
            "anchor": "p%03d" % counter,
            "page": page,
            "text": text,
            "sentences": split_sentences(text),
        })

    def flush_section():
        nonlocal cur_paras
        flush_para()
        if cur_paras:
            sections.append({"name": cur_name, "start_page": start_page, "paragraphs": cur_paras})
        cur_paras = []

    for kind, val in body_lines:
        if kind == "PAGE":
            flush_para()
            page = val
            continue
        line = val
        s = line.strip()
        if not s:
            flush_para()
            continue
        if re.match(r"^\d{1,3}$", s):  # 纯页码
            continue
        head = match_heading(s)
        if head:
            flush_section()
            cur_name, start_page = head, page
            continue
        cur_buf.append(s)
    flush_section()

    doc = {"source_file": os.path.basename(args.input), "pages": page,
           "sections": len(sections),
           "paragraphs": sum(len(s["paragraphs"]) for s in sections)}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"doc": doc, "sections": sections}, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "doc": doc,
                      "names": [s["name"] for s in sections]}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
