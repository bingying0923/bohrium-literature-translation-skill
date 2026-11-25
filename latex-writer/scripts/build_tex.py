#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组装可编译的 LaTeX 源文件：转义、结构、标签、引用。

用法:
    python3 build_tex.py --doc work/doc.json --out main.tex [--template templates/article.tex]

doc.json:
    {"title": "", "authors": [], "abstract": "", "sections": [
        {"heading": "", "text": "", "equations": ["E = mc^2"], "table": {"caption": "", "rows": [["a","b"]]},
         "label": "sec:intro"}]}
"""
import argparse
import json
import os
import re
import sys

ESCAPE = [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
          ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
          ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")]


def esc(text):
    out = text
    for a, b in ESCAPE:
        out = out.replace(a, b)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--template", default=None)
    args = ap.parse_args()

    with open(args.doc, "r", encoding="utf-8-sig") as f:
        doc = json.load(f)

    lines = []
    if args.template and os.path.exists(args.template):
        lines.append(open(args.template, encoding="utf-8").read().rstrip())
    else:
        lines += [
            r"\documentclass[11pt]{article}",
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage{amsmath,amssymb}",
            r"\usepackage{booktabs}",
            r"\usepackage{graphicx}",
            r"\usepackage{hyperref}",
            "",
        ]
    lines += [r"\title{%s}" % esc(doc.get("title", "")),
              r"\author{%s}" % r" \and ".join(esc(a) for a in doc.get("authors", []) or [""]),
              r"\date{}",
              r"\begin{document}",
              r"\maketitle", ""]
    if doc.get("abstract"):
        lines += [r"\begin{abstract}", esc(doc["abstract"]), r"\end{abstract}", ""]

    for i, s in enumerate(doc.get("sections", []), start=1):
        heading = esc(s.get("heading", "Section %d" % i))
        lines.append(r"\section{%s}" % heading)
        if s.get("label"):
            lines.append(r"\label{%s}" % s["label"])
        lines.append("")
        if s.get("text"):
            lines.append(esc(s["text"]))
            lines.append("")
        for eq in s.get("equations", []) or []:
            lines += [r"\begin{equation}", eq, r"\end{equation}", ""]
        table = s.get("table")
        if table and table.get("rows"):
            rows = table["rows"]
            ncol = max(len(r) for r in rows)
            lines.append(r"\begin{table}[htbp]")
            lines.append(r"\centering")
            if table.get("caption"):
                lines.append(r"\caption{%s}" % esc(table["caption"]))
            lines.append(r"\begin{tabular}{%s}" % ("l" * ncol))
            lines.append(r"\toprule")
            for j, row in enumerate(rows):
                cells = [esc(str(c)) for c in row] + [""] * (ncol - len(row))
                lines.append(" & ".join(cells) + r" \\")
                if j == 0:
                    lines.append(r"\midrule")
            lines.append(r"\bottomrule")
            lines.append(r"\end{tabular}")
            lines.append(r"\end{table}")
            lines.append("")

    if doc.get("bibliography"):
        lines += [r"\bibliographystyle{%s}" % doc.get("bibstyle", "plain"),
                  r"\bibliography{%s}" % doc["bibliography"], ""]
    lines.append(r"\end{document}")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps({"status": "ok", "out": args.out, "lines": len(lines),
                      "sections": len(doc.get("sections", []))}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
