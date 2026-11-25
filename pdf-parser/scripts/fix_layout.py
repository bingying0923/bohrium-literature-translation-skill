#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""版面修复：去页眉页脚、双栏重排、输出带锚点的文本块。

用法:
    python3 fix_layout.py --input layout.txt --out work/blocks.json [--columns auto|1|2]

输入约定:
    - 页边界：[page N] 或换页符 \\f
    - 文本来源：pdftotext -layout 或平台 pdf-text-tool 的版面文本（保留列间空格）

输出:
    {"doc":{...},"pages":[{"page":n,"columns":k,"blocks":[{"anchor","col","text","y"}]}]}
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

PAGE_RE = re.compile(r"^\[page\s*(\d+)\]$", re.I)
GAP_RE = re.compile(r"\s{3,}")
HEAD_LIKE = re.compile(r"^(?:\d+(?:\.\d+)*\.?\s+)?(abstract|introduction|related work|background|"
                       r"methods?|materials and methods|results?|discussion|conclusions?|"
                       r"references|acknowledge?ments?|limitations?|appendix)\b", re.I)
CAPTION_LIKE = re.compile(r"^(figure|fig\.?|table|scheme)\s*\d+", re.I)


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
    return pages or [(1, text.split("\n"))]


def page_columns(lines):
    """单页判定：行内存在 ≥3 空格间隙、且左右段都 >8 字符的行占比 ≥50% 视为双栏。"""
    multi = 0
    total = 0
    for ln in lines:
        if not ln.strip():
            continue
        total += 1
        parts = [p for p in GAP_RE.split(ln.strip()) if p.strip()]
        if len(parts) >= 2 and len(parts[0]) > 8 and len(parts[-1]) > 8:
            multi += 1
    if total < 6:
        return 1
    return 2 if multi / total >= 0.5 else 1


def strip_running_heads(pages):
    """去掉在多页重复出现且很短的页眉/页脚行。"""
    seen = Counter()
    for _no, lines in pages:
        for ln in lines:
            s = ln.strip()
            if 0 < len(s) <= 90 and not re.match(r"^\d{1,3}$", s):
                seen[s] += 1
    repeated = {s for s, c in seen.items() if c >= 2 and len(s) <= 90}
    out = []
    for no, lines in pages:
        keep = []
        for ln in lines:
            s = ln.strip()
            if s in repeated and len(s) < 90:
                # 只剔除位于页首/页尾 2 行内的重复行
                idx = lines.index(ln)
                if idx < 2 or idx >= len(lines) - 2:
                    continue
            keep.append(ln)
        out.append((no, keep))
    return out


def split_two_columns(lines):
    """把双栏页按长间隙切成左右两栏文本（先左后右）。

    左栏若是短标题，单独成段，避免与右栏正文粘成一块。
    """
    left, right = [], []
    for ln in lines:
        if not ln.strip():
            left.append("")
            continue
        parts = [p for p in GAP_RE.split(ln.rstrip()) if p.strip()]
        if len(parts) >= 2:
            head = parts[0].strip()
            left.append(head)
            if len(head) <= 50 and (HEAD_LIKE.match(head) or CAPTION_LIKE.match(head)):
                left.append("")
            right.append(" ".join(parts[1:]))
        else:
            left.append(parts[0] if parts else "")
    return "\n".join(left), "\n".join(right)


def blocks_from_text(text, page, col, start_anchor):
    """按空行切块；图表题注单独成块。锚点连续。"""
    blocks, buf = [], []
    idx = start_anchor

    def flush():
        nonlocal buf, idx
        if not buf:
            return
        idx += 1
        blocks.append({"anchor": "b%04d" % idx, "page": page, "col": col,
                       "text": " ".join(x.strip() for x in buf), "y": len(buf)})
        buf = []

    for ln in text.split("\n"):
        if not ln.strip():
            flush()
            continue
        if CAPTION_LIKE.match(ln.strip()) and len(ln.strip()) < 260:
            flush()
            buf = [ln]
            flush()
            continue
        if HEAD_LIKE.match(ln.strip()) and len(ln.strip()) <= 60:
            flush()
            buf = [ln]
            flush()
            continue
        buf.append(ln)
    flush()
    return blocks, idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--columns", default="auto")
    args = ap.parse_args()

    raw = read_text(args.input)
    pages = split_pages(raw)
    pages = strip_running_heads(pages)

    forced = 1 if args.columns == "1" else (2 if args.columns == "2" else 0)

    out_pages, anchor, detected = [], 0, []
    for no, lines in pages:
        cols = forced or page_columns(lines)
        detected.append(cols)
        if cols == 2:
            left, right = split_two_columns(lines)
            lb, anchor = blocks_from_text(left, no, 1, anchor)
            rb, anchor = blocks_from_text(right, no, 2, anchor)
            blocks = lb + rb
        else:
            text = "\n".join(lines)
            blocks, anchor = blocks_from_text(text, no, 1, anchor)
        out_pages.append({"page": no, "columns": cols, "blocks": blocks})

    doc = {"source_file": os.path.basename(args.input), "pages": len(out_pages),
           "columns": detected[0] if detected else 1, "columns_per_page": detected,
           "blocks": sum(len(p["blocks"]) for p in out_pages)}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"doc": doc, "pages": out_pages}, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "out": args.out, "doc": doc}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())

