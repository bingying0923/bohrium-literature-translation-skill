#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成 result.json（可选调用 TeX 编译）+ build_report.md。

用法:
    python3 make_result.py --case-json /input/case.json --tex main.tex --lint work/lint.json \
        --out /app/output/result.json [--compile]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys


def load(path, default=None):
    if not path or not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def try_compile(tex_path):
    engine = None
    for cand in ("latexmk", "pdflatex", "xelatex"):
        if shutil.which(cand):
            engine = cand
            break
    if not engine:
        return {"available": False, "engine": None,
                "note": "本机未安装 TeX 发行版，仅做静态检查；交付前需在目标模板环境实测编译"}
    cmd = [engine, "-interaction=nonstopmode", "-halt-on-error", os.path.basename(tex_path)]
    try:
        proc = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(tex_path)),
                              capture_output=True, text=True, timeout=120)
        return {"available": True, "engine": engine, "returncode": proc.returncode,
                "log_tail": (proc.stdout or "")[-1500:]}
    except Exception as e:
        return {"available": True, "engine": engine, "error": str(e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-json", default=None)
    ap.add_argument("--tex", required=True)
    ap.add_argument("--lint", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--compile", action="store_true")
    args = ap.parse_args()

    case = load(args.case_json, {}) or {}
    lint = load(args.lint, {}) or {}
    build = try_compile(args.tex) if args.compile else {"available": False, "skipped": True}

    status = "success" if lint.get("ok") else "partial"
    if build.get("available") and build.get("returncode") not in (0, None):
        status = "partial"

    result = {
        "case_id": case.get("case_id") or case.get("id") or "unknown",
        "status": status,
        "deliverable": {"path": os.path.basename(args.tex), "kind": "latex"},
        "lint": {"ok": lint.get("ok", False), "errors": lint.get("errors", 0),
                 "warnings": lint.get("warnings", 0), "issues": lint.get("issues", [])},
        "build": build,
        "unresolved": [{"where": "line %s" % i.get("line"), "issue": i.get("issue"),
                        "suggested_action": "修复后重跑 lint_tex.py"}
                       for i in lint.get("issues", []) if i.get("level") == "error"],
        "artifacts": [{"path": os.path.basename(args.tex), "kind": "latex"},
                      {"path": "build_report.md", "kind": "markdown"}],
    }
    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    md = ["# LaTeX 构建报告（%s）" % result["case_id"], "",
          "- 静态检查：%s（错误 %d，警告 %d）" % ("通过" if lint.get("ok") else "未通过",
                                              lint.get("errors", 0), lint.get("warnings", 0)),
          "- 编译：%s" % ("未执行" if not args.compile else
                        ("成功" if build.get("returncode") == 0 else "失败：" + str(build.get("note") or build.get("error") or ""))),
          ""]
    if lint.get("issues"):
        md.append("| 行 | 级别 | 问题 |")
        md.append("|---|---|---|")
        for i in lint["issues"][:50]:
            md.append("| %s | %s | %s |" % (i.get("line"), i.get("level"), i.get("issue")))
    with open(os.path.join(out_dir, "build_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(json.dumps({"status": "ok", "out": args.out, "case_status": status,
                      "errors": lint.get("errors", 0), "warnings": lint.get("warnings", 0)},
                     ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
