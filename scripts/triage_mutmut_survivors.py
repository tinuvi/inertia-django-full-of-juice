#!/usr/bin/env python3
"""Bucket mutmut survivors by mutation shape to guide test-writing triage.

Project-agnostic: classification keys come purely from the diff shape, not
from any project-specific constant table.

    HIGH-VALUE   -> almost always worth killing with a new test
    LOW-VALUE    -> accept as survivor (logger noise, no-op)
    UNKNOWN      -> inspect manually; heuristics were not confident

Run inside the integration-tests container (uses mutmut from the same venv).

    # Fetch + classify in one shot. --target is the file stem (no .py),
    # e.g. "http" for inertia/http.py.
    docker compose run --remove-orphans --rm integration-tests \\
      python scripts/triage_mutmut_survivors.py --target http

    # Narrow to one function / bucket:
    docker compose run --remove-orphans --rm integration-tests \\
      python scripts/triage_mutmut_survivors.py \\
        --target http --function page_data --bucket boolean_flip

    # Re-triage a prior dump (skip fetch) by passing a path instead of --target:
    docker compose run --remove-orphans --rm integration-tests \\
      python scripts/triage_mutmut_survivors.py /app/_survivor_diffs.txt

Exit code: 0 always (reporting tool).
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field

_logger = logging.getLogger("inertia_django_full_of_juice")

# --- parsing -----------------------------------------------------------------

_MUTANT_HEADER_RE = re.compile(r"^=== (?P<mid>[\w\.ǁ]+) ===\s*$")
_FUNC_FROM_MID_RE = re.compile(r"\.x_?(?P<fn>[A-Za-z_][\w]*?)__mutmut_\d+$")
_HUNK_OLD_RE = re.compile(r"^-(?!--)(?P<body>.*)$")
_HUNK_NEW_RE = re.compile(r"^\+(?!\+\+)(?P<body>.*)$")


@dataclass
class Mutant:
    mid: str
    function: str
    old_lines: list[str] = field(default_factory=list)
    new_lines: list[str] = field(default_factory=list)

    @property
    def old(self) -> str:
        return "\n".join(line.strip() for line in self.old_lines if line.strip())

    @property
    def new(self) -> str:
        return "\n".join(line.strip() for line in self.new_lines if line.strip())


def _function_from_mid(mid: str) -> str:
    """Pull the leaf function name out of a mutmut-encoded id.

    Class-method ids look like ``inertia.http.xǁClassǁmethod__mutmut_3``;
    free-function ids look like ``inertia.http.x_method__mutmut_3``.
    """
    if "ǁ" in mid:
        leaf = mid.split("ǁ")[-1]
        return re.sub(r"__mutmut_\d+$", "", leaf)
    match = _FUNC_FROM_MID_RE.search(mid)
    return match.group("fn") if match else "<module>"


def parse_diffs(text: str) -> list[Mutant]:
    mutants: list[Mutant] = []
    current: Mutant | None = None
    for raw in text.splitlines():
        header = _MUTANT_HEADER_RE.match(raw)
        if header:
            if current is not None:
                mutants.append(current)
            mid = header.group("mid")
            current = Mutant(mid=mid, function=_function_from_mid(mid))
            continue
        if current is None:
            continue
        if raw.startswith(("--- ", "+++ ", "@@", "# ")):
            continue
        m_old = _HUNK_OLD_RE.match(raw)
        if m_old:
            current.old_lines.append(m_old.group("body"))
            continue
        m_new = _HUNK_NEW_RE.match(raw)
        if m_new:
            current.new_lines.append(m_new.group("body"))
    if current is not None:
        mutants.append(current)
    return mutants


# --- classification ----------------------------------------------------------

# Buckets are ordered — the first matching rule wins. High-specificity rules
# come before generic ones so, e.g., "logger with a None arg" is tagged as
# logger noise instead of generic arg-to-None.
_LOW_VALUE = {"logger_noise", "noop"}
_HIGH_VALUE = {
    "short_circuit_flip",
    "comparison_flip",
    "boolean_flip",
    "arg_to_none",
    "kwarg_removed",
    "default_value_change",
    "number_change",
    "string_change",
    "operator_change",
    "identifier_swap",
}

_LOGGER_RE = re.compile(r"_logger\.|logger\.")
_COMPARISON_PAIRS = [
    ("==", "!="),
    ("!=", "=="),
    ("<=", ">"),
    (">=", "<"),
    ("<", ">="),
    (">", "<="),
    (" is ", " is not "),
    (" is not ", " is "),
    (" in ", " not in "),
    (" not in ", " in "),
]
_BOOL_PAIRS = [("True", "False"), ("False", "True")]
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
_STRING_LITERAL_RE = re.compile(r"""(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')""")
_KWARG_REMOVED_RE = re.compile(r",\s*\)")
_ARG_TO_NONE_RES = (re.compile(r"\(None\b"), re.compile(r",\s*None\b"), re.compile(r"=\s*None\b"))
_OPS = ["+", "-", "*", "/", "//", "%", "**", "&", "|", "^", "<<", ">>"]


def _has_word(text: str, word: str) -> bool:
    return re.search(rf"(^|[^A-Za-z_]){re.escape(word)}([^A-Za-z_]|$)", text) is not None


def _short_circuit_flip(old: str, new: str) -> bool:
    return ((" and " in old) != (" and " in new)) and ((" or " in old) != (" or " in new))


def _comparison_flip(old: str, new: str) -> bool:
    # Count-based: True iff any pair's `a` count decreases while its `b` count
    # increases. Handles cases like " in " -> " not in " where " in " still
    # appears in the new string inside " not in ".
    return any(old.count(a) > new.count(a) and new.count(b) > old.count(b) for a, b in _COMPARISON_PAIRS)


def _boolean_flip(old: str, new: str) -> bool:
    return any(_has_word(old, a) and _has_word(new, b) for a, b in _BOOL_PAIRS)


def _number_change(old: str, new: str) -> bool:
    o, n = _NUMBER_RE.findall(old), _NUMBER_RE.findall(new)
    return o != n and bool(o or n)


def _string_change(old: str, new: str) -> bool:
    return _STRING_LITERAL_RE.findall(old) != _STRING_LITERAL_RE.findall(new)


def _arg_to_none(old: str, new: str) -> bool:
    return any(rx.search(new) and not rx.search(old) for rx in _ARG_TO_NONE_RES)


def _default_value_change(old: str, new: str) -> bool:
    return ".get(" in old and ".get(" in new and old != new


def _operator_change(old: str, new: str) -> bool:
    o = [op for op in _OPS if op in old]
    n = [op for op in _OPS if op in new]
    return o != n and bool(o or n)


def _identifier_swap(old: str, new: str) -> bool:
    ids_in = lambda s: set(re.findall(r"\b[A-Za-z_]\w*\b", s))
    return ids_in(old) != ids_in(new)


def _kwarg_removed(old: str, new: str) -> bool:
    return _KWARG_REMOVED_RE.search(new) is not None and _KWARG_REMOVED_RE.search(old) is None


def classify(m: Mutant) -> str:
    old, new = m.old, m.new
    if _LOGGER_RE.search(old) or _LOGGER_RE.search(new):
        return "logger_noise"
    if old == new:
        return "noop"
    if _short_circuit_flip(old, new):
        return "short_circuit_flip"
    if _comparison_flip(old, new):
        return "comparison_flip"
    if _boolean_flip(old, new):
        return "boolean_flip"
    if _kwarg_removed(old, new):
        return "kwarg_removed"
    if _arg_to_none(old, new):
        return "arg_to_none"
    if _default_value_change(old, new):
        return "default_value_change"
    if _number_change(old, new):
        return "number_change"
    if _string_change(old, new):
        return "string_change"
    if _operator_change(old, new):
        return "operator_change"
    if _identifier_swap(old, new):
        return "identifier_swap"
    return "unknown"


# --- reporting ---------------------------------------------------------------


def group_by_bucket_and_function(mutants: list[Mutant]) -> dict[str, dict[str, list[Mutant]]]:
    grouped: dict[str, dict[str, list[Mutant]]] = defaultdict(lambda: defaultdict(list))
    for m in mutants:
        grouped[classify(m)][m.function].append(m)
    return grouped


_SEP = "=" * 78
_SUBSEP = "-" * 78


def _bucket_tier(bucket: str) -> str:
    if bucket in _LOW_VALUE:
        return "low"
    if bucket in _HIGH_VALUE:
        return "high"
    return "unknown"


def render(
    grouped: dict[str, dict[str, list[Mutant]]],
    *,
    function_filter: str | None,
    bucket_filter: str | None,
    show_diffs: bool,
) -> str:
    out: list[str] = []
    total = 0
    tier_totals = {"high": 0, "low": 0, "unknown": 0}

    bucket_order = sorted(_HIGH_VALUE) + ["unknown"] + sorted(_LOW_VALUE)
    for b in grouped:
        if b not in bucket_order:
            bucket_order.append(b)

    for bucket in bucket_order:
        functions = grouped.get(bucket)
        if not functions:
            continue
        if bucket_filter and bucket != bucket_filter:
            continue
        bucket_count = sum(len(v) for v in functions.values())
        tier = _bucket_tier(bucket)
        tier_totals[tier] += bucket_count
        total += bucket_count

        out.append(_SEP)
        out.append(f"BUCKET: {tier.upper():7} :: {bucket:28} ({bucket_count})")
        out.append(_SEP)
        for function in sorted(functions):
            if function_filter and function != function_filter:
                continue
            muts = functions[function]
            out.append(f"  [function: {function}]  ({len(muts)})")
            for m in muts:
                out.append(f"    - {m.mid}")
                if show_diffs:
                    for line in m.old_lines:
                        out.append(f"        - {line}")
                    for line in m.new_lines:
                        out.append(f"        + {line}")
            out.append("")

    out.append(_SEP)
    out.append("SUMMARY")
    out.append(_SEP)
    out.append(f"  Total survivors parsed: {total}")
    out.append(f"  HIGH-value (attack):    {tier_totals['high']}")
    out.append(f"  UNKNOWN   (inspect):    {tier_totals['unknown']}")
    out.append(f"  LOW-value (accept):     {tier_totals['low']}")
    out.append("")
    out.append("  Counts per bucket:")
    for bucket in bucket_order:
        functions = grouped.get(bucket)
        if not functions:
            continue
        n = sum(len(v) for v in functions.values())
        out.append(f"    {_bucket_tier(bucket):7} {bucket:28} {n:4}")

    out.append("")
    out.append("  Per function (HIGH / LOW / UNKNOWN / total):")
    per_fn_tiers: dict[str, dict[str, int]] = defaultdict(lambda: {"high": 0, "low": 0, "unknown": 0})
    for bucket, functions in grouped.items():
        tier = _bucket_tier(bucket)
        for fn, muts in functions.items():
            per_fn_tiers[fn][tier] += len(muts)
    for fn in sorted(per_fn_tiers):
        c = per_fn_tiers[fn]
        tot = c["high"] + c["low"] + c["unknown"]
        out.append(f"    {fn:45} {c['high']:4} / {c['low']:4} / {c['unknown']:4} / {tot:4}")

    return "\n".join(out)


# --- fetching from mutmut ----------------------------------------------------


def fetch_survivor_diffs(target_stem: str) -> str:
    """Synthesize the concatenated `mutmut show` dump for every surviving mutant
    whose source file's stem is ``target_stem`` (e.g. ``"http"`` for ``inertia/http.py``).

    Uses mutmut's Python API directly rather than shelling out to ``mutmut show``
    per-mutant, which is ~1.5s × N_survivors — easily several minutes on a
    module with many surviving mutants.
    """
    from difflib import unified_diff

    import libcst as cst
    from mutmut.__main__ import (
        SourceFileMutationData,
        ensure_config_loaded,
        read_mutant_function,
        read_mutants_module,
        read_original_function,
        status_by_exit_code,
        walk_source_files,
    )

    ensure_config_loaded()

    chunks: list[str] = []
    survivor_count = 0
    for path in walk_source_files():
        path_str = str(path)
        if not path_str.endswith(".py"):
            continue
        if path.stem != target_stem:
            continue
        m = SourceFileMutationData(path=path)
        m.load()
        module = read_mutants_module(path)
        for mid, exit_code in m.exit_code_by_key.items():
            if status_by_exit_code[exit_code] != "survived":
                continue
            orig_code = cst.Module([read_original_function(module, mid)]).code.strip()
            mutant_code = cst.Module([read_mutant_function(module, mid)]).code.strip()
            diff = "\n".join(
                unified_diff(
                    orig_code.split("\n"),
                    mutant_code.split("\n"),
                    fromfile=path_str,
                    tofile=path_str,
                    lineterm="",
                )
            )
            chunks.append(f"=== {mid} ===\n# {mid}: survived\n{diff}\n")
            survivor_count += 1

    if survivor_count == 0:
        _logger.warning("triage: no surviving mutants found for target %r.", target_stem)
    else:
        _logger.info("triage: synthesized diffs for %d survivors.", survivor_count)
    return "".join(chunks)


# --- cli ---------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "input",
        nargs="?",
        default=None,
        help=(
            "Path to a pre-generated `mutmut show` dump (one `=== <mid> ===` "
            "header per mutant). Omit when using --target. Use '-' for stdin."
        ),
    )
    p.add_argument(
        "--target",
        help=(
            "File stem (no .py, no path) of the module under test, e.g. 'http' "
            "for inertia/http.py. When set, the script reads survivors from "
            "the local mutants.sqlite — no pre-dumped file needed. "
            "Mutually exclusive with a positional input."
        ),
    )
    p.add_argument("--function", help="Only show survivors whose function name matches exactly.")
    p.add_argument("--bucket", help="Only show survivors in the given bucket (e.g. arg_to_none, logger_noise).")
    p.add_argument("--no-diffs", action="store_true", help="Hide the mutation diff lines under each mutant id.")
    p.add_argument("--save-dump", metavar="PATH", help="With --target: also write the fetched diffs to PATH for later re-triage.")
    args = p.parse_args(argv)
    if args.target and args.input:
        p.error("--target and a positional input path are mutually exclusive.")
    if not args.target and not args.input:
        args.input = "-"
    return args


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    args = parse_args(argv)
    if args.target:
        text = fetch_survivor_diffs(args.target)
        if args.save_dump and text:
            with open(args.save_dump, "w", encoding="utf-8") as fh:
                fh.write(text)
    elif args.input == "-":
        text = sys.stdin.read()
    else:
        with open(args.input, encoding="utf-8") as fh:
            text = fh.read()
    mutants = parse_diffs(text)
    grouped = group_by_bucket_and_function(mutants)
    report = render(
        grouped,
        function_filter=args.function,
        bucket_filter=args.bucket,
        show_diffs=not args.no_diffs,
    )
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
