#!/usr/bin/env python3
"""Build code-reference matrices from the numbered FR/DP/PV source layout.

Rows are FR test folders. Columns are DP source folders. R means that code in
one DP branch names the folder of a DP in another branch. Treat R as a
possible influence that the model must explain. A dot means that the scan
found no reference. A dot does not prove a zero, because shared state,
resources, data, and configuration do not show in names. T means that test
text in the paired FR folder names the paired DP. Tests are not executed.
A question mark means that this paired test reference is missing.

The scan reads UTF-8 files up to 2,000,000 bytes, including comments and
strings. It does not resolve imports, aliases, generated code, or dynamic
calls. It skips hidden paths and the directories in SKIP_DIRS. It reports
other skipped paths as errors. It never follows symlinks.

--spec reads a restricted static subset of one core .ad.hcl file or of the
immediate *.ad.hcl members of a directory. It is not full HCL or ADHCL
validation. It rejects manifests, attachments, decision blocks, evidence
blocks, heredocs, templates, and computed expressions. FIELDS lists the
supported blocks and fields. Separate attributes need separate lines.
Unsupported or malformed input stops the model comparison with an error.

The comparison checks the selected DPs, FRs, and PVs against the folders. It
compares cross-branch references with the authored influence records and
the `cells` defaults. A reference counts for its own cell and for each
ancestor cell. A reference beside an authored zero is a review warning, or
an error under --expect. Conditions and premises are reported, not resolved.

--expect uncoupled forbids every cross-branch reference. --expect decoupled
forbids reference cycles. Take the value from the model's classification.
Exit codes: 0 no error findings, 1 error findings, 2 invalid command line.
Python 3.9 or later. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

LABEL = r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*"
NAME_RE = re.compile(rf"^(fr|dp|pv)([0-9]+(?:_[0-9]+)*)_({LABEL})$")
RESERVED_RE = re.compile(r"^(fr|dp|pv)(?:[0-9_]|$)", re.I)
ALIAS_RE = re.compile(r"^(FR|DP|PV)([0-9]+(?:\.[0-9]+)*)$")
SKIP_DIRS = {"node_modules", "__pycache__", "build", "dist", "target", "vendor"}
MAX_BYTES = 2_000_000
Num = tuple


def fmt(num: Num) -> str:
    return ".".join(map(str, num))


def is_prefix(a: Num, b: Num) -> bool:
    return b[:len(a)] == a


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


class Report:
    def __init__(self) -> None:
        self.findings = []

    def error(self, message: str) -> None:
        finding = ("error", message)
        if finding not in self.findings:
            self.findings.append(finding)

    def warn(self, message: str) -> None:
        self.findings.append(("warning", message))

    def note(self, message: str) -> None:
        self.findings.append(("note", message))

    @property
    def errors(self) -> int:
        return sum(severity == "error" for severity, _ in self.findings)


def symlink_component(path):
    return next((part for part in (path, *path.parents) if part.is_symlink()), None)


def discover(root: Path, kind: str, rep: Report) -> dict:
    nodes = {}
    labels = {}
    link = symlink_component(root)
    if link:
        rep.error(f"skipped symlink: {link}")
        return nodes
    if not root.is_dir():
        rep.error(f"layout root is not a directory: {root}")
        return nodes

    def walk(directory, parent):
        try:
            entries = sorted(directory.iterdir())
        except OSError as exc:
            rep.error(f"skipped unreadable directory {directory}: {exc}")
            return
        for entry in entries:
            if entry.name.startswith(".") or entry.name in SKIP_DIRS:
                continue
            if entry.is_symlink():
                rep.error(f"skipped symlink: {entry}")
                continue
            is_dir = entry.is_dir()
            # A file name ends at its first dot: pv1_map.test.ts belongs to pv1_map.
            name = entry.name if is_dir else entry.name.split(".", 1)[0]
            match = NAME_RE.fullmatch(name)
            if not match:
                if RESERVED_RE.match(name):
                    rep.error(f"malformed numbered layout name: {entry}")
                if is_dir:
                    walk(entry, parent)
                continue
            found_kind, digits, label = match.groups()
            num = tuple(map(int, digits.split("_")))
            if found_kind == kind and is_dir:
                if label in labels:
                    rep.error(f"duplicate {kind.upper()} label {label}: {labels[label]} and {entry}.")
                labels[label] = entry
            if found_kind == "pv" and kind == "dp":
                if parent is None or entry.parent != parent.path:
                    rep.error(f"{entry}: a PV must sit directly inside its DP folder.")
                elif num != parent.num:
                    rep.error(f"{entry}: PV number {fmt(num)} differs from DP{fmt(parent.num)}.")
                else:
                    # Several entries can share one PV label, for example a .h and a .c file.
                    parent.pvs.append((label, entry))
                if is_dir:
                    walk(entry, parent)
                continue
            if not is_dir and parent and found_kind == kind and num == parent.num and label == parent.label:
                continue  # A file named after its own folder, such as dp1_map/dp1_map.go.
            if found_kind != kind or not is_dir:
                rep.error(f"{entry}: expected a {kind} folder, not a {found_kind} entry.")
                continue
            expected_parent = parent.path if parent else root
            expected_num = parent.num if parent else ()
            if entry.parent != expected_parent or num[:-1] != expected_num:
                rep.error(f"{entry}: numbering and nesting must match directly inside {expected_parent}.")
                continue
            if num in nodes:
                rep.error(f"duplicate {kind.upper()}{fmt(num)}: {nodes[num].path} and {entry}.")
                continue
            node = Node(kind, num, label, entry)
            nodes[num] = node
            walk(entry, node)

    walk(root, None)
    return nodes


def iter_files(directory: Path, rep: Report):
    if symlink_component(directory) or not directory.is_dir():
        return

    def onerror(exc):
        rep.error(f"skipped unreadable directory: {exc}")

    for dirpath, dirnames, filenames in os.walk(directory, onerror=onerror, followlinks=False):
        keep = []
        for name in sorted(dirnames):
            path = Path(dirpath) / name
            if name.startswith(".") or name in SKIP_DIRS:
                continue
            if path.is_symlink():
                rep.error(f"skipped symlink: {path}")
            else:
                keep.append(name)
        dirnames[:] = keep
        for name in sorted(filenames):
            if name.startswith("."):
                continue
            path = Path(dirpath) / name
            if path.is_symlink():
                rep.error(f"skipped symlink: {path}")
                continue
            try:
                if not path.is_file():
                    rep.error(f"skipped non-regular path: {path}")
                    continue
                if path.stat().st_size > MAX_BYTES:
                    rep.error(f"skipped oversize file: {path}")
                    continue
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                rep.error(f"skipped unreadable file {path}: {exc}")
                continue
            yield path, text


def owner_of(path: Path, nodes: dict):
    matches = [node for node in nodes.values() if node.path in path.parents]
    return max(matches, key=lambda node: len(node.num)) if matches else None


@dataclass
class Reference:
    row: Num
    col: Num
    where: str


def collect(src, tests, dps, frs, rep):
    if not dps:
        return [], set(), [], []
    names = {node.name: num for num, node in dps.items()}
    token = re.compile(
        rf"(?<![A-Za-z0-9_])(dp[0-9]+(?:_[0-9]+)*_{LABEL})(?![A-Za-z0-9_])"
    )

    def refs(text, path):
        for line, content in enumerate(text.splitlines(), 1):
            found = set()
            for match in token.finditer(content):
                name = match.group(1)
                if name not in names:
                    rep.error(f"{path}:{line}: unknown DP token {name!r}.")
                else:
                    found.add(names[name])
            # A path such as dp2_x/dp2_1_y names its parent only to reach the child.
            for num in sorted(found):
                if not any(other != num and is_prefix(num, other) for other in found):
                    yield line, num

    source, paired, test_refs, observed = [], set(), [], []
    for path, text in iter_files(src, rep):
        owner = owner_of(path, dps)
        for line, target in refs(text, path):
            where = f"{path}:{line}"
            # Files directly in the source root, such as src/lib.rs, compose like app/.
            if src / "app" in path.parents or path.parent == src:
                if len(target) > 1:
                    rep.error(f"{where}: the composition root names nested {dps[target].name}. Compose it through its parent DP.")
            elif src / "shared" in path.parents:
                rep.error(f"{where}: shared names {dps[target].name}.")
            elif owner:
                observed.append(Reference(owner.num, target, where))
                if not is_prefix(owner.num, target) and not is_prefix(target, owner.num):
                    source.append(Reference(owner.num, target, where))
            else:
                rep.error(f"{where}: a DP name sits outside a DP folder, app/, or the source root.")
    for path, text in iter_files(tests, rep):
        owner = owner_of(path, frs)
        for line, target in refs(text, path):
            if owner:
                test_refs.append(Reference(owner.num, target, f"{path}:{line}"))
                if is_prefix(owner.num, target):
                    paired.add(owner.num)
    # A descendant's exact paired token also supplies a parent-scope token.
    for num in list(paired):
        paired.update(num[:depth] for depth in range(1, len(num)))
    return source, paired, test_refs, observed


def leaves(nodes):
    return [num for num in sorted(nodes) if not any(
        len(other) > len(num) and is_prefix(num, other) for other in nodes
    )]


def pattern(axis, edges):
    before = {num: set() for num in axis}
    for row, col in edges:
        if row != col:
            before[row].add(col)
    order, done = [], set()
    while len(order) < len(axis):
        ready = [num for num in axis if num not in done and before[num] <= done]
        if not ready:
            return "cyclic", []
        order.append(ready[0])
        done.add(ready[0])
    return ("acyclic" if any(before.values()) else "diagonal"), order


def render_scope(title, axis, source, paired, complete, rep, expect):
    # Project descendants upward. Never project a parent token into leaf facts.
    def place(num):
        inside = [member for member in axis if is_prefix(member, num)]
        if inside:
            return inside[0]
        # A strict ancestor of a member sits above this scope's level.
        return "above" if any(is_prefix(num, member) for member in axis) else None

    cells = {}
    unresolved = []
    for ref in source:
        row, col = place(ref.row), place(ref.col)
        if row is None or col is None:
            continue  # The reference belongs to another scope.
        if "above" in (row, col):
            unresolved.append(ref)
        elif row != col:
            cells.setdefault((row, col), []).append(ref)
    graph, order = pattern(axis, cells)
    missing = [num for num in axis if num not in paired]
    result = graph if complete and not missing and not unresolved else "incomplete"
    width = max([len("DP" + fmt(num)) for num in axis] + [5])
    row_width = max([len("FR" + fmt(num)) for num in axis] + [5])
    out = [title, " " * (row_width + 2) + " ".join(
        ("DP" + fmt(num)).rjust(width) for num in axis
    )]
    for row in axis:
        values = [
            ("T" if row in paired else "?") if row == col
            else ("R" if (row, col) in cells else ".")
            for col in axis
        ]
        out.append(("FR" + fmt(row)).ljust(row_width + 2) + " ".join(
            value.rjust(width) for value in values
        ))
    out.append(f"reference pattern: {result}" + (f"; observed graph: {graph}" if result == "incomplete" else ""))
    if graph == "acyclic":
        out.append("DP order: " + ", ".join("DP" + fmt(num) for num in order))
    for (row, col), refs in sorted(cells.items()):
        out.append(f"  FR{fmt(row)} <- DP{fmt(col)}: " + ", ".join(dict.fromkeys(ref.where for ref in refs)))
    for ref in unresolved:
        out.append(f"  unresolved parent scope: FR{fmt(ref.row)} <- DP{fmt(ref.col)} at {ref.where}")
    if expect == "decoupled" and graph == "cyclic":
        rep.error(f"{title}: source-reference cycle violates --expect decoupled.")
    return out + [""]


# This is a static syntax reader, not a second ADHCL assessor.
FIELDS = {
    "design": "boundary level workload",
    "source": "title doi url pages",
    "stakeholder": "role",
    "need": "statement why stakeholder",
    "constraint": "statement kind",
    "assumption": "statement status",
    "context": "description assumes excludes workload",
    "workload": "description ranges",
    "state": "description",
    "fr": "statement need parent bounded_by alias",
    "criterion": "statement metric op value unit under allocated_from",
    "dp": "controls responsibility decision why role owns_state reads_state bounded_by holds_if alias",
    "pv": "realizes kind address note alias",
    "influence": "from to effect mechanism because mechanism_source source under holds_if",
    "cells": "scope unlisted because",
    "coupling": "scope affects reason condition decision normal_practice residual_risk iteration_bound convergence stopping failure_behavior",
    "module": "realizes contains within inputs outputs owns_state dependencies invariants failure_behavior acceptance_checks alias",
    "flow": "steps owner input output after",
    "loop": "after back_to when bound",
    "scenario": "kind verifies vary expect_affected expect_unaffected steps description under",
    "expect": "scope classification order basis under",
}
# Child block kinds by parent kind. Every other block is top-level only.
CHILDREN = {"fr": "criterion", "flow": "loop"}
UNNAMED = {"influence", "loop"}


class SpecError(ValueError):
    pass


@dataclass(frozen=True)
class Ref:
    value: str


@dataclass
class Block:
    kind: str
    label: str | None
    attrs: dict
    children: list
    where: str


class StaticReader:
    TOKEN = re.compile(
        r'(?P<space>[ \t\r]+)|(?P<newline>\n)|(?P<comment>\#[^\n]*|//[^\n]*|/\*.*?\*/)'
        r'|(?P<string>"(?:[^"\\\n]|\\.)*")|(?P<number>-?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)'
        r'|(?P<name>[a-z][a-z0-9_]*)|(?P<punct>[{}=\[\],.])',
        re.S,
    )

    def __init__(self, text, path):
        self.path = path
        self.tokens = []
        offset = 0
        line = 1
        while offset < len(text):
            match = self.TOKEN.match(text, offset)
            if not match:
                raise SpecError(f"{path}:{line}: unsupported or malformed static syntax near {text[offset:offset + 24]!r}.")
            kind, value = match.lastgroup, match.group()
            if kind not in {"space", "comment"}:
                self.tokens.append((kind, value, line))
            offset = match.end()
            line += value.count("\n")
        self.tokens.append(("end", "", line))
        self.i = 0

    def at(self, value):
        return self.tokens[self.i][1] == value

    def take(self, value=None, kind=None):
        token = self.tokens[self.i]
        if (value is not None and token[1] != value) or (kind is not None and token[0] != kind):
            self.fail(f"expected {value or kind}, got {token[1]!r}")
        self.i += 1
        return token[1]

    def fail(self, message):
        raise SpecError(f"{self.path}:{self.tokens[self.i][2]}: {message}.")

    def newlines(self):
        while self.tokens[self.i][0] == "newline":
            self.i += 1

    def value(self):
        kind, value, _ = self.tokens[self.i]
        if kind == "string":
            self.i += 1
            if "${" in value or "%{" in value:
                self.fail("templates are not supported")
            try:
                return json.loads(value)
            except ValueError:
                self.fail("unsupported quoted string escape")
        if self.at("{"):
            self.take("{")
            result = {}
            self.newlines()
            while not self.at("}"):
                kind = self.tokens[self.i][0]
                if kind == "string":
                    key = self.value()
                elif kind == "name":
                    key = self.take(kind="name")
                else:
                    self.fail("object keys need literal strings or identifiers")
                if key in result:
                    self.fail(f"duplicate object key {key!r}")
                self.take("=")
                result[key] = self.value()
                if self.at(","):
                    self.take(",")
                elif not self.at("}") and self.tokens[self.i][0] != "newline":
                    self.fail("object items need a comma or separate lines")
                self.newlines()
            self.take("}")
            return result
        if self.at("["):
            self.take("[")
            items = []
            self.newlines()
            while not self.at("]"):
                items.append(self.value())
                self.newlines()
                if self.at("]"):
                    break
                self.take(",")
                self.newlines()
            self.take("]")
            return items
        if kind == "number":
            self.i += 1
            return ("number", value)
        if kind == "name":
            name = self.take(kind="name")
            if name in {"true", "false"}:
                return name == "true"
            if not self.at("."):
                self.fail("only literal values and static traversals are supported")
            while self.at("."):
                self.take(".")
                name += "." + self.take(kind="name")
            return Ref(name)
        self.fail("unsupported value")

    def block(self, parent=None):
        where = f"{self.path}:{self.tokens[self.i][2]}"
        kind = self.take(kind="name")
        if kind not in FIELDS or (parent and CHILDREN.get(parent) != kind) or (not parent and kind in CHILDREN.values()):
            self.fail(f"unsupported block {kind!r}")
        label = None if kind in UNNAMED else self.take(kind="string")
        if label is not None:
            try:
                label = json.loads(label)
            except ValueError:
                self.fail("invalid block label")
            if not re.fullmatch(LABEL, label):
                self.fail("invalid block label")
        self.take("{")
        attrs, children = {}, []
        self.newlines()
        while not self.at("}"):
            if self.tokens[self.i][0] == "end":
                self.fail("unclosed block")
            if self.tokens[self.i][0] != "name":
                self.fail("expected an attribute or supported child block")
            if self.tokens[self.i + 1][1] != "=":
                children.append(self.block(kind))
            else:
                name = self.take(kind="name")
                allowed = set(FIELDS[kind].split())
                if kind != "source":
                    allowed.update(("cites", "origin"))
                if name not in allowed:
                    self.fail(f"unsupported field {kind}.{name}")
                if name in attrs:
                    self.fail(f"duplicate attribute {name}")
                self.take("=")
                attrs[name] = self.value()
                if self.tokens[self.i][0] != "newline" and not self.at("}"):
                    self.fail("separate attributes need separate lines")
            self.newlines()
        self.take("}")
        return Block(kind, label, attrs, children, where)

    def read(self):
        blocks = []
        self.newlines()
        while self.tokens[self.i][0] != "end":
            blocks.append(self.block())
            self.newlines()
        if not blocks:
            self.fail("empty spec input")
        return blocks


def read_spec(path):
    link = symlink_component(path)
    if link:
        raise SpecError(f"skipped symlink spec: {link}")
    files = sorted(path.glob("*.ad.hcl")) if path.is_dir() else [path]
    if path.is_dir():
        excluded = sorted(path.glob("*.ad.project.hcl")) + sorted(path.glob("*.ad.ext.hcl"))
        if excluded:
            raise SpecError(f"unsupported manifest or attachment in spec input: {excluded[0]}")
    if not files:
        raise SpecError(f"empty spec directory: {path}")
    blocks = []
    for file in files:
        if file.name.endswith((".ad.project.hcl", ".ad.ext.hcl")):
            raise SpecError(f"unsupported manifest or attachment spec: {file}")
        if file.is_symlink():
            raise SpecError(f"skipped symlink spec: {file}")
        if not file.name.endswith(".ad.hcl"):
            raise SpecError(f"spec input needs a .ad.hcl core file: {file}")
        if file.stat().st_size > MAX_BYTES:
            raise SpecError(f"skipped oversize spec: {file}")
        blocks.extend(StaticReader(file.read_text(encoding="utf-8"), file).read())
    return blocks


def check_spec(spec, root, src, tests, dps, frs, source, rep, expect=None):
    try:
        blocks = read_spec(spec)
        identities = {}
        for block in blocks:
            if block.label is not None:
                identity = block.kind + "." + block.label
                if identity in identities:
                    raise SpecError(f"{block.where}: duplicate label {identity}.")
                identities[identity] = block
            for child in (child for child in block.children if child.label is not None):
                identity = f"{block.kind}.{block.label}.{child.kind}.{child.label}"
                if identity in identities:
                    raise SpecError(f"{child.where}: duplicate label {identity}.")
                identities[identity] = child
        if sum(block.kind == "design" for block in blocks) != 1:
            raise SpecError("spec needs exactly one design block.")

        def all_refs(value):
            if isinstance(value, Ref):
                yield value.value
            elif isinstance(value, list):
                for item in value:
                    yield from all_refs(item)
            elif isinstance(value, dict):
                for item in value.values():
                    yield from all_refs(item)

        for block in identities.values():
            for value in block.attrs.values():
                for target in all_refs(value):
                    if target not in identities:
                        raise SpecError(f"{block.where}: unresolved reference {target}.")
        for block in blocks:
            if block.kind == "influence":
                for value in block.attrs.values():
                    for target in all_refs(value):
                        if target not in identities:
                            raise SpecError(f"{block.where}: unresolved reference {target}.")

        def string(block, name, required=False):
            value = block.attrs.get(name)
            if value is None and not required:
                return None
            if not isinstance(value, str) or not value.strip():
                raise SpecError(f"{block.where}: {block.kind}.{name} needs a nonblank literal string.")
            return value

        required_strings = {
            "design": ("boundary",), "source": ("title",),
            "stakeholder": ("role",), "need": ("statement",),
            "constraint": ("statement",), "assumption": ("statement",),
            "context": ("description",), "workload": ("description",),
            "state": ("description",), "fr": ("statement",),
        }
        for block in blocks:
            for name in required_strings.get(block.kind, ()):
                string(block, name, True)

        def refs(block, name, kind, single=False, required=False):
            value = block.attrs.get(name)
            if value is None and not required:
                return []
            values = [value] if single else value
            kinds = kind.split("|")
            if not isinstance(values, list) or not values or any(
                not isinstance(item, Ref) or item.value.split(".")[0] not in kinds
                or len(item.value.split(".")) != 2 for item in values
            ):
                raise SpecError(f"{block.where}: {block.kind}.{name} needs {'one reference' if single else 'a nonempty reference list'} to {kind}.")
            targets = [item.value for item in values]
            if len(targets) != len(set(targets)):
                raise SpecError(f"{block.where}: duplicate reference in {name}.")
            return targets

        fr_blocks = {key: block for key, block in identities.items() if block.kind == "fr"}
        dp_blocks = {key: block for key, block in identities.items() if block.kind == "dp"}
        parents = {key: refs(block, "parent", "dp", single=True) for key, block in fr_blocks.items()}
        controls = {key: refs(block, "controls", "fr", required=True) for key, block in dp_blocks.items()}
        active_dp = set()
        for key, block in dp_blocks.items():
            decision = string(block, "decision", True)
            if decision not in {"selected", "proposed", "rejected", "superseded"}:
                raise SpecError(f"{block.where}: unsupported DP decision {decision!r}.")
            string(block, "responsibility", True)
            if decision == "selected":
                active_dp.add(key)
        active_fr = {key for key, parent in parents.items() if not parent or parent[0] in active_dp}
        pv_targets = {
            "pv." + block.label: refs(block, "realizes", "dp", required=True)
            for block in blocks if block.kind == "pv"
        }
        active_pv = {
            key for key, targets in pv_targets.items()
            if any(target in active_dp for target in targets)
        }
        active_identities = active_fr | active_dp | active_pv
        numbers, used = {}, {}
        for key, block in identities.items():
            if key not in active_identities:
                continue
            alias = string(block, "alias")
            match = ALIAS_RE.fullmatch(alias or "")
            if not match or match[1].lower() != block.kind:
                raise SpecError(f"{block.where}: {key} needs a numbered {block.kind.upper()} alias for this layout profile.")
            num = tuple(map(int, match[2].split(".")))
            alias_key = (block.kind, num)
            if block.kind != "pv":
                if alias_key in used:
                    raise SpecError(f"{block.where}: duplicate numbered alias {alias} for {key} and {used[alias_key]}.")
                used[alias_key] = key
            numbers[key] = num
        for key in active_dp:
            num = numbers[key]
            targets = controls[key]
            if len(targets) != 1 or targets[0] not in active_fr or numbers[targets[0]] != num:
                raise SpecError(f"{key}: selected DP needs one active FR with the same number.")
            parent = parents[targets[0]]
            if (parent and numbers[parent[0]] != num[:-1]) or (not parent and len(num) != 1):
                raise SpecError(f"{key}: numbered parent does not match the controlled FR parent.")
        for kind, active, found, base in (
            ("dp", active_dp, dps, src), ("fr", active_fr, frs, tests)
        ):
            expected = {numbers[key]: key.split(".")[1] for key in active}
            for num, label in sorted(expected.items()):
                if num not in found or found[num].label != label:
                    rep.error(f"spec {kind}.{label}: missing or renamed {kind.upper()}{fmt(num)} folder in {base}.")
            for num, node in found.items():
                if num not in expected:
                    rep.error(f"{node.path}: no active {kind.upper()}{fmt(num)} in spec.")
        expected_pvs = {}
        for block in blocks:
            if block.kind != "pv":
                continue
            key = "pv." + block.label
            targets = pv_targets[key]
            if key not in active_pv:
                continue
            if len(targets) != 1:
                raise SpecError(f"{key}: this layout needs exactly one realized DP.")
            num = numbers[targets[0]]
            if numbers[key] != num:
                raise SpecError(f"{key}: PV{fmt(numbers[key])} number differs from realized DP{fmt(num)}.")
            expected_pvs.setdefault(num, set()).add(block.label)
            node = dps.get(num)
            hits = [path for label, path in node.pvs if label == block.label] if node else []
            if not hits:
                rep.error(f"spec {key}: no matching PV entry inside DP{fmt(num)}.")
            address = string(block, "address")
            if hits and address:
                actual = {str(path.relative_to(root)) if root in path.parents else str(path) for path in hits}
                actual.update(str(Path(path).with_suffix("")) for path in list(actual))
                if address.rstrip("/") not in actual:
                    rep.error(f"spec {key}: address {address!r} does not match {hits[0]}.")
        for num, node in dps.items():
            for label, path in node.pvs:
                if label not in expected_pvs.get(num, set()):
                    rep.error(f"{path}: PV entry has no active spec record.")

        def premises(block):
            return refs(block, "holds_if", "assumption") if block.attrs.get("holds_if") != [] else []

        # Each claim is (dp key, fr key, effect, conditions).
        claims = []
        for block in blocks:
            if block.kind != "influence":
                continue
            froms = refs(block, "from", "dp", required=True)
            target = refs(block, "to", "fr", single=True, required=True)[0]
            effect = string(block, "effect", True)
            if effect not in {"none", "material", "unknown"}:
                raise SpecError(f"{block.where}: invalid influence effect {effect!r}.")
            if effect in {"none", "material"}:
                string(block, "because" if effect == "none" else "mechanism", True)
            under = refs(block, "under", "context|workload", single=True)
            for origin in froms:
                conditions = list(dict.fromkeys(under + premises(block) + premises(dp_blocks[origin])))
                claims.append((origin, target, effect, conditions))
        explicit = {(origin, target) for origin, target, _, _ in claims}
        for block in blocks:
            if block.kind != "cells":
                continue
            scope = refs(block, "scope", "design|dp", single=True, required=True)[0]
            unlisted = string(block, "unlisted", True)
            if unlisted not in {"none", "unknown"}:
                raise SpecError(f"{block.where}: invalid cells default {unlisted!r}.")
            if unlisted == "none":
                string(block, "because", True)
            owner = None if scope.startswith("design.") else scope
            set_frs = [key for key, parent in parents.items() if (parent[0] if parent else None) == owner]
            set_dps = [key for key, targets in controls.items() if set(targets) & set(set_frs)]
            claims += [
                (origin, target, unlisted, premises(dp_blocks[origin]))
                for origin in set_dps for target in set_frs if (origin, target) not in explicit
            ]

        # A reference supports its own cell and every ancestor cell.
        def covers(cell, ref):
            return is_prefix(cell[0], ref.row) and is_prefix(cell[1], ref.col)

        cells, inactive = {}, 0
        for origin, target, effect, conditions in claims:
            if origin not in active_dp or target not in active_fr:
                inactive += 1
                continue
            cells.setdefault((numbers[target], numbers[origin]), []).append((effect, conditions))
        for (row, col), entries in sorted(cells.items()):
            hits = [ref for ref in source if covers((row, col), ref)]
            zeros = ["; ".join(conditions) or "unconditional" for effect, conditions in entries if effect == "none"]
            cell = f"FR{fmt(row)} <- DP{fmt(col)}"
            if hits and zeros:
                message = (f"the model states zero for {cell} ({' | '.join(zeros)}), "
                           f"but {hits[0].where} names DP{fmt(hits[0].col)}.")
                if expect:
                    rep.error(f"{message} This violates --expect {expect}. Remove the reference, or change the design with the user's approval.")
                else:
                    rep.warn(f"REVIEW WARNING: {message} Review the effect under those conditions.")
            elif not hits and any(effect == "material" for effect, _ in entries) and not (
                    is_prefix(row, col) or is_prefix(col, row)):
                rep.note(f"the model states a material effect for {cell}, but no code reference shows it. The effect can use data or a shared resource.")
        for ref in source:
            if not any(covers(cell, ref) for cell in cells):
                rep.warn(f"{ref.where}: code for DP{fmt(ref.row)} names DP{fmt(ref.col)}, but the model has no influence record for FR{fmt(ref.row)} <- DP{fmt(ref.col)} or an ancestor cell.")
        if inactive:
            rep.note(f"{inactive} influence claims name an inactive DP or FR. They were not compared.")
        retained = sorted({block.kind for block in blocks if block.kind in {"expect", "coupling", "module", "flow", "scenario"}})
        if retained:
            rep.note(f"The comparison did not assess these block kinds: {', '.join(retained)}.")
        rep.note("Spec limits: conditions and premises are not resolved. Unknown claims remain unknown. Support is not assessed. Full HCL and ADHCL validation did not run.")
    except (SpecError, OSError, UnicodeError, RecursionError) as exc:
        rep.error(f"spec comparison stopped: {exc}")


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=".", help="project root; PV addresses are relative to it")
    parser.add_argument("--src", help="source root (default ROOT/src)")
    parser.add_argument("--tests", help="test root (default ROOT/tests)")
    parser.add_argument("--spec", help="restricted static core file or directory; not full HCL validation")
    parser.add_argument("--expect", choices=["uncoupled", "decoupled"], help="structural policy taken from the model's classification")
    args = parser.parse_args(argv)
    # Keep lexical paths so root symlinks remain visible to the scanner.
    root = Path(os.path.abspath(args.root))
    src = Path(os.path.abspath(args.src)) if args.src else root / "src"
    tests = Path(os.path.abspath(args.tests)) if args.tests else root / "tests"
    rep = Report()
    dps = discover(src, "dp", rep)
    frs = discover(tests, "fr", rep)
    if not dps or not frs:
        rep.error("empty DP or FR inventory. The reference pattern is incomplete.")
    for num in sorted(set(dps) - set(frs)):
        rep.error(f"DP{fmt(num)} has no paired FR test folder.")
    for num in sorted(set(frs) - set(dps)):
        rep.error(f"FR{fmt(num)} has no paired DP source folder.")
    for num in leaves(dps):
        if not dps[num].pvs:
            rep.error(f"{dps[num].name} is a leaf DP with no PV entry.")
    source, paired, test_refs, observed = collect(src, tests, dps, frs, rep)
    for num in sorted(set(dps) & set(frs) - paired):
        rep.error(f"FR{fmt(num)} has no paired-test token for DP{fmt(num)} or its subtree.")
    complete = not rep.errors
    out = [f"Code-reference matrices: {src}  tests: {tests}",
           "Rows are FRs, columns are DPs. R = cross-branch code reference; T = paired DP named in test text (not executed); . = no reference found; ? = paired test reference missing.", ""]
    scopes = {}
    for num in sorted(set(dps) | set(frs)):
        scopes.setdefault(num[:-1], []).append(num)
    if not scopes:
        out.append("reference pattern: incomplete")
    for parent, axis in scopes.items():
        title = "Scope " + ("DP" + fmt(parent) if parent else "design root")
        out += render_scope(title, axis, source, paired, complete, rep, args.expect)
    master = sorted(set(leaves(dps)) | set(leaves(frs)))
    if len(scopes) > 1:
        out += render_scope("Scope master (leaf FRs by leaf DPs)", master, source, paired, complete, rep, args.expect)
    if args.expect == "uncoupled" and source:
        rep.error(f"{len(source)} cross-branch code references violate --expect uncoupled. Each one is listed under 'Source-text references across branches'.")
    graph, _ = pattern(sorted(dps), {(ref.row, ref.col) for ref in source})
    if args.expect == "decoupled" and graph == "cyclic":
        rep.error("A cycle of cross-branch code references violates --expect decoupled.")
    out.append("Source-text references across branches")
    out.extend(f"  FR{fmt(ref.row)} <- DP{fmt(ref.col)}: {ref.where}" for ref in source)
    if not source:
        out.append("  none observed")
    out.append("Other source-text references (own subtree or ancestor; excluded from the cross-branch graph)")
    out.extend(f"  FR{fmt(ref.row)} <- DP{fmt(ref.col)}: {ref.where}" for ref in observed if ref not in source)
    out.append("Test-text references (not executed; excluded from the source graph)")
    out.extend(f"  FR{fmt(ref.row)} <- DP{fmt(ref.col)}: {ref.where}" for ref in test_refs)
    if not test_refs:
        out.append("  none observed")
    if args.spec:
        check_spec(Path(os.path.abspath(args.spec)), root, src, tests, dps, frs, source, rep, args.expect)
    out += ["", "Findings"]
    out += [f"- {severity}: {message}" for severity, message in rep.findings] or ["- none"]
    out += ["", f"Errors: {rep.errors}",
            "A dot means that no reference was found. It does not prove a zero.",
            "A clean result does not prove independence. Shared state and resources do not show in code references."]
    print("\n".join(out))
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
