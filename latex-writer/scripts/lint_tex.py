#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LaTeX 静态检查：括号/环境/引用/标签/表格列数/非 ASCII/宏包重复。

用法:
    python3 lint_tex.py --tex main.tex [--bib refs.bib] --out work/lint.json
"""
import argparse
import json
import os
import re
import sys

BEGIN = re.compile(r"\\begin\{([^}]+)\}")
END = re.compile(r"\\end\{([^}]+)\}")
LABEL = re.compile(r"\\label\{([^}]+)\}")
REF = re.compile(r"\\(?:ref|eqref|autoref|cref)\{([^}]+)\}")
CITE = re.compile(r"\\cite[pt]?\{([^}]+)\}")
USEPKG = re.compile(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}")
BIBKEY = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,")
TABULAR = re.compile(r"\\begin\{tabular\}\{([^}]*)\}")
NONASCII = re.compile(r"[^\x00-\x7F]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", required=True)
    ap.add_argument("--bib", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    text = open(args.tex, encoding="utf-8", errors="ignore").read()
    lines = text.split("\n")
    issues = []

    # 1) 花括号平衡
    depth = 0
    for i, ln in enumerate(lines, start=1):
        depth += ln.count("{") - ln.count("}")
        if depth < 0:
            issues.append({"line": i, "level": "error", "issue": "多余的 }"})
            depth = 0
    if depth != 0:
        issues.append({"line": len(lines), "level": "error", "issue": "花括号不平衡（缺 %d 个 }）" % depth})

    # 2) 环境配对
    stack = []
    for i, ln in enumerate(lines, start=1):
        for m in BEGIN.finditer(ln):
            stack.append((m.group(1), i))
        for m in END.finditer(ln):
            if not stack:
                issues.append({"line": i, "level": "error", "issue": "\\end{%s} 没有对应的 \\begin" % m.group(1)})
                continue
            env, start = stack.pop()
            if env != m.group(1):
                issues.append({"line": i, "level": "error",
                               "issue": "环境不匹配：第 %d 行 \\begin{%s} 与第 %d 行 \\end{%s}" % (start, env, i, m.group(1))})
    for env, start in stack:
        issues.append({"line": start, "level": "error", "issue": "\\begin{%s} 未闭合" % env})

    # 3) 文档结构
    if "\\documentclass" not in text:
        issues.append({"line": 1, "level": "error", "issue": "缺 \\documentclass"})
    if "\\begin{document}" not in text:
        issues.append({"line": 1, "level": "error", "issue": "缺 \\begin{document}"})
    if "\\end{document}" not in text:
        issues.append({"line": len(lines), "level": "error", "issue": "缺 \\end{document}"})

    # 4) 引用与标签
    labels = set(LABEL.findall(text))
    for i, ln in enumerate(lines, start=1):
        for m in REF.finditer(ln):
            for key in m.group(1).split(","):
                if key.strip() and key.strip() not in labels:
                    issues.append({"line": i, "level": "error", "issue": "\\ref{%s} 无对应 \\label" % key.strip()})
    if args.bib and os.path.exists(args.bib):
        bibkeys = set(BIBKEY.findall(open(args.bib, encoding="utf-8", errors="ignore").read()))
        for i, ln in enumerate(lines, start=1):
            for m in CITE.finditer(ln):
                for key in m.group(1).split(","):
                    if key.strip() and key.strip() not in bibkeys:
                        issues.append({"line": i, "level": "error", "issue": "\\cite{%s} 在 .bib 中不存在" % key.strip()})

    # 5) 表格列数与 & 数
    for i, ln in enumerate(lines, start=1):
        m = TABULAR.search(ln)
        if m:
            ncol = len(re.sub(r"[^lcrp]", "", m.group(1)))
            j = i
            while j < len(lines) and "\\end{tabular}" not in lines[j]:
                row = lines[j]
                if "&" in row and "\\\\" in row:
                    got = row.count("&") + 1
                    if got != ncol:
                        issues.append({"line": j + 1, "level": "warning",
                                       "issue": "表格列数不匹配：声明 %d 列，本行 %d 列" % (ncol, got)})
                j += 1

    # 6) 非 ASCII
    bad = [(i, ln) for i, ln in enumerate(lines, start=1) if NONASCII.search(ln) and not ln.strip().startswith("%")]
    if bad:
        issues.append({"line": bad[0][0], "level": "warning",
                       "issue": "含非 ASCII 字符 %d 行，需 XeLaTeX/ctex 或先转义" % len(bad)})

    # 7) 宏包重复
    pkgs = {}
    for i, ln in enumerate(lines, start=1):
        for m in USEPKG.finditer(ln):
            for p in m.group(1).split(","):
                p = p.strip()
                if p in pkgs:
                    issues.append({"line": i, "level": "warning",
                                   "issue": "宏包 %s 重复加载（首次在第 %d 行）" % (p, pkgs[p])})
                else:
                    pkgs[p] = i

    errors = [i for i in issues if i["level"] == "error"]
    out = {"issues": issues, "errors": len(errors), "warnings": len(issues) - len(errors),
           "ok": not errors}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "errors": len(errors), "warnings": out["warnings"]}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
