#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按"首次出现顺序"重排参考文献编号，合并重复条目，并同步正文标记。

用法:
    python3 renumber.py --refs work/refs.json --out work/revised.json [--keep-duplicates]

输出 revised.json: {body, entries, mapping, merged, changes}
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_refs import NUM_CITE, expand  # noqa: E402


def render_numbers(nums):
    if not nums:
        return "[]"
    nums = sorted(set(nums))
    parts, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        parts.append(str(nums[i]) if j == i else "%d-%d" % (nums[i], nums[j]))
        i = j + 1
    return "[" + ",".join(parts) + "]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep-duplicates", action="store_true")
    args = ap.parse_args()

    with open(args.refs, "r", encoding="utf-8") as f:
        data = json.load(f)
    body = data.get("body", "")
    cites = data.get("citations", [])
    entries = data.get("entries", [])

    # 1) 重复条目：同一 key 归到最小原编号
    dup_map = {}
    if not args.keep_duplicates:
        by_key = {}
        for e in sorted(entries, key=lambda x: x["index"]):
            k = e.get("key")
            if not k:
                continue
            if k in by_key:
                dup_map[e["index"]] = by_key[k]
            else:
                by_key[k] = e["index"]

    def canon(n):
        return dup_map.get(n, n)

    # 2) 首次出现顺序（重复项只占一个位置），未被引用的接在后面
    order = []
    for c in cites:
        for n in (c.get("numbers") or []):
            c2 = canon(n)
            if c2 not in order:
                order.append(c2)
    for e in sorted(entries, key=lambda x: x["index"]):
        c2 = canon(e["index"])
        if c2 not in order:
            order.append(c2)

    # 3) 连续编号 1..N
    new_index = {old: i + 1 for i, old in enumerate(order)}
    mapping = {}
    for e in entries:
        mapping[e["index"]] = new_index[canon(e["index"])]

    changes = []

    def replace(m):
        nums = expand(m.group(1))
        new_nums = [mapping.get(n, n) for n in nums]
        rendered = render_numbers(new_nums)
        if rendered != render_numbers(nums):
            changes.append({"old": m.group(0), "new": rendered,
                            "numbers_old": nums, "numbers_new": new_nums})
        return rendered

    new_body = NUM_CITE.sub(replace, body)

    # 4) 条目：只保留每个 canonical 的第一条，按新编号排序、编号连续
    kept, seen = [], set()
    for e in sorted(entries, key=lambda x: x["index"]):
        c = canon(e["index"])
        if c in seen:
            continue
        seen.add(c)
        e2 = dict(e)
        e2["old_index"] = e["index"]
        e2["index"] = new_index[c]
        kept.append(e2)
    kept.sort(key=lambda x: x["index"])

    out = {"body": new_body, "entries": kept, "mapping": mapping,
           "merged": dup_map, "changes": changes,
           "stats": {"entries": len(kept), "changed_markers": len(changes)}}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"status": "ok", "entries": len(kept),
                      "merged": len(dup_map), "changed_markers": len(changes)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
