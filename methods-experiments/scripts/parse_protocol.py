#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析实验记录：步骤 / 参数表 / 数据集。

用法:
    python3 parse_protocol.py --protocol protocol.md [--config config.json] --out work/parsed.json
"""
import argparse
import json
import os
import re
import sys

STEP_RE = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
PARAM_LINE = re.compile(r"^\s*\|(.+)\|\s*$")
KV = re.compile(r"(\w[\w\s\-]*?)\s*[:：]\s*([^;；|]+)")
IO_RE = re.compile(r"input\s*[:：]\s*([^;；|]+)|output\s*[:：]\s*([^;；|]+)|condition\s*[:：]\s*([^;；|]+)", re.I)


def read(path):
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return open(path, "r", encoding=enc).read().replace("\r\n", "\n")
        except (UnicodeDecodeError, LookupError):
            continue
    return open(path, "r", encoding="utf-8", errors="ignore").read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--config", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    text = read(args.protocol)
    steps, params, datasets = [], [], []
    section = ""

    for ln in text.split("\n"):
        s = ln.strip()
        if not s:
            continue
        if re.match(r"^#{1,6}\s*", s):
            section = re.sub(r"^#{1,6}\s*", "", s).lower()
            continue
        m = STEP_RE.match(ln)
        if m and ("step" in section or "步骤" in section or not section):
            body = m.group(2)
            io = {"input": "", "output": "", "condition": ""}
            for mm in IO_RE.finditer(body):
                if mm.group(1):
                    io["input"] = mm.group(1).strip()
                if mm.group(2):
                    io["output"] = mm.group(2).strip()
                if mm.group(3):
                    io["condition"] = mm.group(3).strip()
            clean = IO_RE.sub("", body).strip(" ;；")
            steps.append({"n": int(m.group(1)), "text": clean, **io})
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not cells or set("".join(cells)) <= set("-: "):
                continue
            low = [c.lower() for c in cells]
            if low[0] in ("name", "参数", "parameter", "名称"):
                continue
            if "param" in section or "参数" in section or len(cells) >= 4:
                params.append({"name": cells[0], "value": cells[1] if len(cells) > 1 else "",
                               "unit": cells[2] if len(cells) > 2 else "",
                               "target": cells[3] if len(cells) > 3 else "",
                               "source": cells[4] if len(cells) > 4 else "protocol",
                               "verified": True})
            continue
        if s.startswith("- ") and ("dataset" in section or "数据" in section):
            kv = {k.strip(): v.strip() for k, v in KV.findall(s)}
            datasets.append({"name": kv.get("name", ""), "version": kv.get("version", ""),
                             "n": int(kv["n"]) if kv.get("n", "").isdigit() else kv.get("n", ""),
                             "split": kv.get("split", ""), "preprocess": kv.get("preprocess", ""),
                             "use": kv.get("use", "")})
            continue
        if "reproduce" in section or "复现" in section:
            kv = {k.lower().strip(): v.strip() for k, v in KV.findall(s)}
            if kv:
                datasets.append({"__reproduce__": kv})

    reproduce = {}
    for d in list(datasets):
        if "__reproduce__" in d:
            reproduce.update(d["__reproduce__"])
            datasets.remove(d)

    if args.config and os.path.exists(args.config):
        cfg = json.load(open(args.config, encoding="utf-8-sig"))
        flat = {}

        def walk(obj, prefix=""):
            for k, v in (obj.items() if isinstance(obj, dict) else []):
                if isinstance(v, dict):
                    walk(v, prefix + k + ".")
                else:
                    flat[(prefix + k).lower()] = v
        walk(cfg)
        for p in params:
            key = p["name"].lower().replace(" ", "_")
            for fk, fv in flat.items():
                if fk.endswith(key) or key in fk:
                    p["value"] = str(fv)
                    p["source"] = "config"
                    break

    out = {"steps": steps, "params": params, "datasets": datasets, "reproduce": reproduce}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "steps": len(steps), "params": len(params),
                      "datasets": len(datasets)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
