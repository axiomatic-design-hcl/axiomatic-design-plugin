#!/usr/bin/env python3
"""Rebuild axiomatic design matrices from an FR/DP/PV source layout.

The layout contract is in ../references/layout-contract.md. This checker reads
folder names and scans file text for references to other `dp` folders. A
reference is structural evidence that one DP can change another DP's FR. The
absence of a reference does not prove a zero: shared runtime resources, data,
and configuration are invisible to this scan.

Usage:
  ad_layout_check.py [--root DIR] [--src DIR] [--tests DIR] [--spec PATH]
                     [--expect uncoupled|decoupled]

Exit codes: 0 no error findings, 1 error findings, 2 invalid command line.
Python 3.9 or later, standard library only.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

LABEL = r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*"
NAME_RE = re.compile(rf"^(fr|dp|pv)([0-9]+(?:_[0-9]+)*)_({LABEL})$")
ALIAS_RE = re.compile(r"^(FR|DP|PV)([0-9]+(?:\.[0-9]+)*)$")
SKIP_DIRS = {"node_modules", "__pycache__", "build", "dist", "target", "vendor"}
MAX_BYTES = 2_000_000

Num = tuple  # (2, 1) for FR2.1 / DP2.1


def fmt(num: Num) -> str:
    return ".".join(str(n) for n in num)


def is_prefix(a: Num, b: Num) -> bool:
    """True when a is b or an ancestor of b."""
    return b[: len(a)] == a


@dataclass
class Node:
    kind: str
    num: Num
    label: str
    path: Path
    pvs: list = field(default_factory=list)

    @property
    def name(self) -> str:
        return f"{self.kind}{'_'.join(map(str, self.num))}_{self.label}"


@dataclass
class Finding:
    severity: str
    message: str

    def __str__(self) -> str:
        return f"- {self.severity}: {self.message}"


class Report:
    def __init__(self) -> None:
        self.findings: list[Finding] = []

    def error(self, msg: str) -> None:
        self.findings.append(Finding("error", msg))

    def warn(self, msg: str) -> None:
        self.findings.append(Finding("warning", msg))

    def note(self, msg: str) -> None:
        self.findings.append(Finding("note", msg))

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == "error")


# ── Layout discovery ─────────────────────────────────────────


def discover(root: Path, kind: str, rep: Report) -> dict:
    """Map number tuples to Node for every `kind` folder below root."""
    nodes: dict = {}
    if not root.is_dir():
        return nodes

    def walk(directory: Path, parent: Node | None) -> None:
        for entry in sorted(directory.iterdir()):
            if entry.name.startswith(".") or entry.name in SKIP_DIRS:
                continue
            m = NAME_RE.match(entry.stem if entry.is_file() else entry.name)
            if m and m.group(1) == "pv" and kind == "dp":
                if parent is None:
                    rep.error(f"{entry} is a pv outside any dp folder.")
                elif tuple(map(int, m.group(2).split("_"))) != parent.num:
                    rep.error(f"{entry} has number {m.group(2)}, but its dp folder is {parent.name}.")
                else:
                    parent.pvs.append((m.group(3), entry))
                continue
            if not entry.is_dir():
                continue
            if m and m.group(1) == kind:
                num = tuple(map(int, m.group(2).split("_")))
                expected_depth = 1 if parent is None else len(parent.num) + 1
                if len(num) != expected_depth or (parent and num[:-1] != parent.num):
                    where = parent.name if parent else directory.name
                    rep.error(f"{entry} is numbered {fmt(num)} but sits in {where}; nesting must follow numbering.")
                    continue
                if parent is None and directory != root:
                    rep.error(f"{entry} is a top-level {kind} folder but is not directly inside {root}.")
                    continue
                if num in nodes:
                    rep.error(f"{kind.upper()}{fmt(num)} appears twice: {nodes[num].path} and {entry}.")
                    continue
                node = Node(kind, num, m.group(3), entry)
                nodes[num] = node
                walk(entry, node)
            elif m:
                rep.error(f"{entry} is a {m.group(1)} folder inside {root}; it belongs in the other tree.")
            else:
                walk(entry, parent)

    walk(root, None)
    return nodes


def iter_files(directory: Path):
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS)
        for name in sorted(filenames):
            path = Path(dirpath) / name
            try:
                if path.stat().st_size > MAX_BYTES:
                    continue
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            yield path, text


def owner_of(path: Path, nodes: dict) -> Node | None:
    """Deepest node whose folder contains path."""
    best = None
    for node in nodes.values():
        if node.path in path.parents and (best is None or len(node.num) > len(best.num)):
            best = node
    return best


# ── Evidence collection ──────────────────────────────────────


@dataclass
class Evidence:
    row: Num  # FR number whose outcome may change
    col: Num  # DP number whose change may affect it
    where: str


def collect(src: Path, tests: Path, dps: dict, frs: dict, rep: Report):
    """Return off-diagonal evidence and the set of FR numbers with diagonal evidence."""
    if not dps:
        return [], set()
    names = {node.name: num for num, node in dps.items()}
    token = re.compile(
        r"(?<![A-Za-z0-9_])(" + "|".join(sorted(map(re.escape, names), key=len, reverse=True)) + r")(?![A-Za-z0-9_])"
    )
    edges: list[Evidence] = []
    diagonal: set = set()

    def refs(text: str):
        for i, line in enumerate(text.splitlines(), 1):
            for m in token.finditer(line):
                yield i, names[m.group(1)]

    app, shared = src / "app", src / "shared"
    for path, text in iter_files(src):
        rel = path.relative_to(src.parent) if src.parent in path.parents else path
        if app == path or app in path.parents:
            for line, target in refs(text):
                if len(target) > 1:
                    rep.error(f"{rel}:{line} in app refers to nested {dps[target].name}; compose through its parent junction.")
            continue
        if shared == path or shared in path.parents:
            for line, target in refs(text):
                rep.error(f"{rel}:{line} in shared refers to {dps[target].name}; shared code must not depend on a DP.")
            continue
        owner = owner_of(path, dps)
        if owner is None:
            rep.warn(f"{rel} is outside every dp folder, app, and shared.")
            continue
        for line, target in refs(text):
            if is_prefix(owner.num, target):
                continue  # own subtree: the parent's junction wires its children
            if is_prefix(target, owner.num):
                continue  # ancestor: contract of a decision fixed earlier
            edges.append(Evidence(owner.num, target, f"{rel}:{line}"))

    for path, text in iter_files(tests):
        rel = path.relative_to(tests.parent) if tests.parent in path.parents else path
        owner = owner_of(path, frs)
        if owner is None:
            continue  # change scenarios and helpers outside any fr folder are not a matrix row
        for line, target in refs(text):
            if is_prefix(owner.num, target):
                diagonal.add(owner.num)
            elif is_prefix(target, owner.num):
                continue
            else:
                edges.append(Evidence(owner.num, target, f"{rel}:{line}"))
    # Parent diagonals: any test below fr<N> that reaches below dp<N>.
    for num in list(diagonal):
        for k in range(1, len(num)):
            diagonal.add(num[:k])
    return edges, diagonal


def related_row(evidence_row: Num, row: Num) -> bool:
    return is_prefix(row, evidence_row) or is_prefix(evidence_row, row)


def cell_evidence(edges, row: Num, col: Num):
    found, seen = [], set()
    for e in edges:
        if related_row(e.row, row) and is_prefix(col, e.col) and e.where not in seen:
            seen.add(e.where)
            found.append(e)
    return found


# ── Matrices ─────────────────────────────────────────────────


def sibling_sets(dps: dict) -> dict:
    sets: dict = {}
    for num in sorted(dps):
        sets.setdefault(num[:-1], []).append(num)
    return sets


def leaves(dps: dict) -> list:
    return [n for n in sorted(dps) if not any(len(m) > len(n) and is_prefix(n, m) for m in dps)]


def classify(axis: list, off: dict) -> tuple:
    """off maps (row, col) to evidence. Return (classification, order)."""
    if not off:
        return "uncoupled", axis
    before = {n: set() for n in axis}  # col must precede row
    for row, col in off:
        before[row].add(col)
    order, done = [], set()
    while len(order) < len(axis):
        ready = [n for n in axis if n not in done and before[n] <= done]
        if not ready:
            return "coupled", []
        order.append(ready[0])
        done.add(ready[0])
    return "decoupled", order


def render(title: str, axis: list, off: dict, diagonal: set) -> list:
    cols = [f"DP{fmt(n)}" for n in axis]
    width = max([len(c) for c in cols] + [5])
    rowh = max(len(f"FR{fmt(n)}") for n in axis)
    lines = [title, " " * (rowh + 2) + " ".join(c.rjust(width) for c in cols)]
    for r in axis:
        cells = []
        for c in axis:
            if r == c:
                cells.append("X" if r in diagonal else "?")
            else:
                cells.append("X" if (r, c) in off else "0")
        lines.append(f"FR{fmt(r)}".ljust(rowh + 2) + " ".join(v.rjust(width) for v in cells))
    return lines


# ── Minimal .ad.hcl reader ───────────────────────────────────


def strip_hcl(text: str) -> str:
    """Blank comments and string contents so that braces can be counted."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "#" or text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", text[i:j]))
            i = j
        elif c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            if j >= n:  # unterminated: blank the rest, keep the length
                out.append(re.sub(r"[^\n]", " ", text[i:]))
                break
            out.append('"' + re.sub(r"[^\n]", " ", text[i + 1 : j]) + '"')
            i = j + 1
        elif text.startswith("<<", i) and (m := re.match(r"<<-?([A-Za-z_]+)\n", text[i:])):
            end = re.search(rf"^\s*{m.group(1)}\s*$", text[i + m.end() :], re.M)
            j = n if end is None else i + m.end() + end.end()
            out.append(re.sub(r"[^\n]", " ", text[i:j]))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def read_spec(path: Path) -> list:
    """Return top-level blocks as (type, label, body text) from a file or directory."""
    files = sorted(path.glob("*.ad.hcl")) if path.is_dir() else [path]
    files = [f for f in files if not f.name.endswith((".ad.ext.hcl", ".ad.project.hcl"))]
    blocks = []
    header = re.compile(r'([a-z_]+)(?:\s+"( *)")?\s*\{')
    for f in files:
        text = f.read_text(encoding="utf-8")
        masked = strip_hcl(text)
        i = 0
        while i < len(masked):
            if masked[i].isspace():
                i += 1
                continue
            m = header.match(masked, i)
            if not m:  # not a block header at depth 0: skip to the next line
                nl = masked.find("\n", i)
                i = len(masked) if nl < 0 else nl + 1
                continue
            depth, j = 0, m.end() - 1
            while j < len(masked):
                depth += {"{": 1, "}": -1}.get(masked[j], 0)
                if depth == 0:
                    break
                j += 1
            label = text[m.start(2) : m.end(2)] if m.group(2) is not None else None
            body, masked_body = text[m.end() : j], masked[m.end() : j]
            # keep only top-level attributes: blank nested blocks
            flat = masked_body
            while re.search(r"\{[^{}]*\}", flat):
                flat = re.sub(r"\{[^{}]*\}", lambda b: " " * len(b.group(0)), flat)
            blocks.append((m.group(1), label, body, flat))
            i = j + 1
    return blocks


def attr_raw(body: str, flat: str, name: str):
    m = re.search(rf"^\s*{name}\s*=", flat, re.M)
    if not m:
        return None
    start, depth, j = m.end(), 0, m.end()
    while j < len(flat):
        ch = flat[j]
        depth += {"[": 1, "(": 1, "]": -1, ")": -1}.get(ch, 0)
        if ch == "\n" and depth <= 0:
            break
        j += 1
    return body[start:j].strip()


def attr_str(body, flat, name):
    raw = attr_raw(body, flat, name)
    m = re.fullmatch(r'"((?:[^"\\]|\\.)*)"', raw or "")
    return m.group(1) if m else None


def attr_refs(body, flat, kind, name):
    raw = attr_raw(body, flat, name) or ""
    return re.findall(rf"\b{kind}\.({LABEL})\b", raw)


def check_spec(spec: Path, root: Path, src: Path, tests: Path, dps: dict, frs: dict, edges, rep: Report) -> None:
    blocks = read_spec(spec)
    fr_spec, dp_spec, pv_spec, infl = {}, {}, [], []
    for kind, label, body, flat in blocks:
        if kind == "fr":
            fr_spec[label] = dict(alias=attr_str(body, flat, "alias"), parent=(attr_refs(body, flat, "dp", "parent") or [None])[0])
        elif kind == "dp":
            dp_spec[label] = dict(
                alias=attr_str(body, flat, "alias"),
                controls=attr_refs(body, flat, "fr", "controls"),
                decision=attr_str(body, flat, "decision"),
            )
        elif kind == "pv":
            pv_spec.append((label, attr_refs(body, flat, "dp", "realizes"), attr_str(body, flat, "address")))
        elif kind == "influence":
            infl.append((attr_refs(body, flat, "dp", "from"), (attr_refs(body, flat, "fr", "to") or [None])[0], attr_str(body, flat, "effect")))

    active_dp = {k for k, v in dp_spec.items() if v["decision"] == "selected"}
    active_fr = set()
    for label, v in fr_spec.items():
        if v["parent"] is None or v["parent"] in active_dp:
            active_fr.add(label)

    def number(kind, label, alias):
        m = ALIAS_RE.match(alias or "")
        if not m or m.group(1) != kind.upper():
            rep.error(f"{kind}.{label} has alias {alias!r}; the layout needs an alias such as {kind.upper()}2.1.")
            return None
        return tuple(map(int, m.group(2).split(".")))

    fr_num = {k: number("fr", k, fr_spec[k]["alias"]) for k in sorted(active_fr)}
    dp_num = {k: number("dp", k, dp_spec[k]["alias"]) for k in sorted(active_dp)}

    for label in sorted(active_dp):
        num, controls = dp_num[label], dp_spec[label]["controls"]
        if num is None:
            continue
        if len(controls) != 1:
            rep.error(f"dp.{label} controls {len(controls)} FRs; the layout pairs one DP folder with one FR folder.")
        elif fr_num.get(controls[0]) not in (None, num):
            rep.error(f"dp.{label} is DP{fmt(num)} but controls FR{fmt(fr_num[controls[0]])}; numbers must pair.")
        parent = fr_spec.get(controls[0], {}).get("parent") if controls else None
        if parent and dp_num.get(parent) is not None and dp_num[parent] != num[:-1]:
            rep.error(f"dp.{label} is DP{fmt(num)} but its parent is DP{fmt(dp_num[parent])}.")

    for kind, spec_nums, found, base in (("dp", dp_num, dps, src), ("fr", fr_num, frs, tests)):
        by_num = {n: k for k, n in spec_nums.items() if n is not None}
        for num, label in sorted(by_num.items()):
            node = found.get(num)
            if node is None:
                rep.error(f"{kind}.{label} ({kind.upper()}{fmt(num)}) has no folder {kind}{'_'.join(map(str, num))}_{label} in {base}.")
            elif node.label != label:
                rep.error(f"{node.path} is named {node.label}, but {kind.upper()}{fmt(num)} is {kind}.{label} in the spec.")
        for num, node in sorted(found.items()):
            if num not in by_num:
                rep.error(f"{node.path} has no active {kind.upper()}{fmt(num)} in the spec.")

    expected_pvs: dict = {}
    for label, realizes, address in pv_spec:
        targets = [d for d in realizes if d in active_dp]
        if not targets:
            continue
        if len(realizes) != 1:
            rep.error(f"pv.{label} realizes {len(realizes)} DPs; the layout places each PV inside one DP folder.")
            continue
        num = dp_num.get(targets[0])
        node = dps.get(num) if num else None
        if node is None:
            continue
        expected_pvs.setdefault(num, set()).add(label)
        hits = [p for pl, p in node.pvs if pl == label]
        if not hits:
            rep.error(f"pv.{label} has no entry pv{'_'.join(map(str, num))}_{label} in {node.path}.")
        elif address:
            actual = {str(p.relative_to(root)) if root in p.parents else str(p) for p in hits}
            actual |= {str(Path(a).with_suffix("")) for a in actual}
            if address.rstrip("/") not in actual:
                rep.error(f"pv.{label} has address {address!r}, but the layout has {sorted(actual)[0]!r}.")
    for num, node in sorted(dps.items()):
        for pl, p in node.pvs:
            if pl not in expected_pvs.get(num, set()):
                rep.error(f"{p} is not a pv of dp.{node.label} in the spec.")

    # Compare code evidence with authored influences.
    claims: dict = {}
    for froms, to, effect in infl:
        if to not in fr_num or fr_num[to] is None:
            continue
        for d in froms:
            if dp_num.get(d) is not None:
                claims[(fr_num[to], dp_num[d])] = effect
    for (row, col), effect in sorted(claims.items()):
        if row == col:
            continue
        found = cell_evidence(edges, row, col)
        if effect == "none" and found:
            where = ", ".join(e.where for e in found[:3])
            rep.error(f"The spec says DP{fmt(col)} has no effect on FR{fmt(row)}, but code refers across: {where}.")
        elif effect == "material" and not found:
            rep.note(f"The spec says DP{fmt(col)} affects FR{fmt(row)}; no code reference shows it (data or runtime path).")
    for e in edges:
        if not any(
            related_row(e.row, row) and is_prefix(col, e.col) and claims[(row, col)] != "unknown"
            for row, col in claims
        ):
            rep.warn(f"{e.where}: FR{fmt(e.row)} code refers to DP{fmt(e.col)}, and the spec states no effect for that cell.")


# ── Main ─────────────────────────────────────────────────────


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", default=".", help="project root; pv addresses are relative to it")
    parser.add_argument("--src", help="source root (default ROOT/src)")
    parser.add_argument("--tests", help="test root (default ROOT/tests)")
    parser.add_argument("--spec", help="a .ad.hcl file or a directory of them")
    parser.add_argument("--expect", choices=["uncoupled", "decoupled"], help="fail when a scope is worse")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    root = Path(args.root).resolve()
    src = Path(args.src).resolve() if args.src else root / "src"
    tests = Path(args.tests).resolve() if args.tests else root / "tests"
    if not src.is_dir():
        print(f"error: source root {src} is not a directory", file=sys.stderr)
        return 2
    if args.spec and not Path(args.spec).exists():
        print(f"error: spec {args.spec} does not exist", file=sys.stderr)
        return 2

    rep = Report()
    dps = discover(src, "dp", rep)
    frs = discover(tests, "fr", rep)
    for num in sorted(set(dps) - set(frs)):
        rep.warn(f"DP{fmt(num)} has no paired tests/fr{'_'.join(map(str, num))}_* folder.")
    for num in sorted(set(frs) - set(dps)):
        rep.error(f"FR{fmt(num)} has no paired src/dp{'_'.join(map(str, num))}_* folder: uncontrolled requirement.")
    for num in leaves(dps):
        if not dps[num].pvs:
            rep.warn(f"{dps[num].name} is a leaf DP with no pv entry.")
    edges, diagonal = collect(src, tests, dps, frs, rep)

    out = [f"Layout: {src}  tests: {tests}", ""]
    order_rank = {"uncoupled": 0, "decoupled": 1, "coupled": 2}
    scopes = [(f"Scope {'design root' if not p else 'DP' + fmt(p)}", axis) for p, axis in sibling_sets(dps).items()]
    master = leaves(dps)
    if len(master) > 1 and len(scopes) > 1:
        scopes.append(("Scope master (leaf FRs by leaf DPs)", master))
    for title, axis in scopes:
        off = {}
        for r in axis:
            for c in axis:
                if r != c and cell_evidence(edges, r, c):
                    off[(r, c)] = cell_evidence(edges, r, c)
        cls, order = classify(axis, off)
        out += render(title, axis, off, diagonal)
        detail = f"structural classification: {cls}"
        if cls == "decoupled":
            detail += "; DP order: " + ", ".join(f"DP{fmt(n)}" for n in order)
        out.append(detail)
        for (r, c), ev in sorted(off.items()):
            out.append(f"  FR{fmt(r)} <- DP{fmt(c)}: " + ", ".join(e.where for e in ev[:3]))
        missing = [n for n in axis if n not in diagonal]
        if missing:
            out.append("  no test reaches its paired DP: " + ", ".join(f"FR{fmt(n)}" for n in missing))
        if args.expect and order_rank[cls] > order_rank[args.expect]:
            rep.error(f"{title} is {cls}; expected {args.expect}.")
        out.append("")

    if args.spec:
        check_spec(Path(args.spec), root, src, tests, dps, frs, edges, rep)

    out.append("Findings")
    out += [str(f) for f in rep.findings] or ["- none"]
    out.append("")
    out.append(f"Errors: {rep.errors}")
    out.append("A 0 means no code reference was found, not that no influence exists.")
    print("\n".join(out))
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
