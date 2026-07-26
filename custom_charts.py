"""PCC 5.x — Custom metrics / charts (GoldenCheetah-style extension).

Status: VIEW layer over the existing generic metric store. PCC already has a
universal metric history (`/api/metrics/history?metric=X`, `db.query_metric_history`)
and manual logging (`/api/metrics/log`). This module lets the athlete DEFINE
saved chart specifications (GoldenCheetah "Custom Charts"): pick a Y metric,
optional X metric (else time), a chart type, and an optional safe derived
expression over up to two metrics (e.g. ratio of two metrics). The underlying
numbers ALWAYS come from the one metric store — single source of truth.

Safety: the derived expression is NOT eval'd. Only a whitelist is allowed:
  - metric tokens: a / b (mapped to two chosen source metrics)
  - operators: + - * /
  - numbers and parentheses
A tiny recursive-descent evaluator runs over the tokenised expression, so no
arbitrary code can execute. If the expression is invalid, the chart falls
back to plotting metric `a` directly.

Storage: <profile_dir>/custom_charts.json (list of definitions).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional


# Whitelisted metric tokens used inside a derived expression.
_TOKEN_RE = re.compile(r"\s*([ab0-9.()+\-*/]+)\s*")


def _safe_eval(expr: str, a: Optional[float], b: Optional[float]) -> Optional[float]:
    """Evaluate a whitelisted expression over a,b (no eval).

    Allowed: tokens `a`, `b`, numbers, `+ - * / ( )`. Returns None on any
    invalid token or division by zero.
    """
    if not expr:
        return a
    # Tokenise strictly; reject anything outside the whitelist.
    tokens = re.findall(r"[ab]|[0-9]+\.?[0-9]*|[+\-*/()]", expr)
    joined = "".join(tokens)
    # Basic sanity: rebuild and ensure it only contains whitelisted chars.
    if re.sub(r"[ab0-9.+\-*/() ]", "", expr):
        return a
    vals = {"a": a, "b": b}

    def parse_add(tokens):
        left = parse_mul(tokens)
        while tokens and tokens[0] in ("+", "-"):
            op = tokens.pop(0)
            right = parse_mul(tokens)
            left = left + right if op == "+" else left - right
        return left

    def parse_mul(tokens):
        left = parse_atom(tokens)
        while tokens and tokens[0] in ("*", "/"):
            op = tokens.pop(0)
            right = parse_atom(tokens)
            if op == "*":
                left = left * right
            else:
                if right == 0:
                    return float("nan")
                left = left / right
        return left

    def parse_atom(tokens):
        if not tokens:
            return float("nan")
        t = tokens.pop(0)
        if t == "(":
            v = parse_add(tokens)
            if tokens and tokens[0] == ")":
                tokens.pop(0)
            return v
        if t in ("a", "b"):
            v = vals.get(t)
            return float(v) if v is not None else float("nan")
        if re.fullmatch(r"[0-9]+\.?[0-9]*", t):
            return float(t)
        return float("nan")

    try:
        toks = re.findall(r"[ab]|[0-9]+\.?[0-9]*|[+\-*/()]", expr)
        result = parse_add(toks)
        if result != result:  # NaN
            return a
        return result
    except Exception:
        return a


def _charts_path() -> Optional[Path]:
    try:
        from profile_manager import ProfileManager
        pm = ProfileManager.get()
        aid = getattr(pm, "_active_id", None) or "default"
        d = Path.home() / ".domestique" / "profiles" / aid
        return d / "custom_charts.json"
    except Exception:
        return None


def load_charts() -> list[dict]:
    p = _charts_path()
    if p and p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")) or []
        except Exception:
            return []
    return []


def save_charts(charts: list[dict]) -> bool:
    p = _charts_path()
    if p is None:
        return False
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(charts, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False


def upsert_chart(defn: dict) -> dict:
    """Validate + store a chart definition; returns the saved record (with id)."""
    title = str(defn.get("title") or "Grafico").strip()[:60]
    y_metric = str(defn.get("y_metric") or "").strip()
    if not y_metric:
        raise ValueError("y_metric required")
    rec = {
        "id": str(defn.get("id") or _new_id()),
        "title": title,
        "y_metric": y_metric,
        "x_metric": (str(defn.get("x_metric") or "").strip() or None),
        "type": str(defn.get("type") or "line"),
        "formula": (str(defn.get("formula") or "").strip() or None),
        "color": (str(defn.get("color") or "#f59e0b").strip() or "#f59e0b"),
    }
    charts = load_charts()
    replaced = False
    for i, c in enumerate(charts):
        if c.get("id") == rec["id"]:
            charts[i] = rec
            replaced = True
            break
    if not replaced:
        charts.append(rec)
    save_charts(charts)
    return rec


def delete_chart(chart_id: str) -> bool:
    charts = load_charts()
    kept = [c for c in charts if c.get("id") != chart_id]
    if len(kept) == len(charts):
        return False
    return save_charts(kept)


def _new_id() -> str:
    import time
    return "cc_" + str(int(time.time() * 1000))


def compute_series(defn: dict, metric_history_fn) -> dict:
    """Build {labels, values} for a chart def from the metric store.

    metric_history_fn(metric, days) -> list[{date,value,...}] (mirrors
    db.query_metric_history). The derived formula (if any) is applied per
    date across the two source metrics.
    """
    days = int(defn.get("days") or 365)
    y_hist = {r["date"]: r["value"] for r in metric_history_fn(defn["y_metric"], days)}
    x_metric = defn.get("x_metric")
    x_hist = {r["date"]: r["value"] for r in metric_history_fn(x_metric, days)} if x_metric else {}
    formula = defn.get("formula")
    labels, values = [], []
    for date in sorted(y_hist.keys()):
        a = y_hist.get(date)
        if a is None:
            continue
        b = x_hist.get(date) if x_metric else None
        v = _safe_eval(formula, a, b) if formula else a
        if v is None or (isinstance(v, float) and v != v):
            continue
        if x_metric:
            xv = x_hist.get(date)
            if xv is None:
                continue
            labels.append(round(xv, 2))
        else:
            labels.append(date)
        values.append(round(v, 3))
    return {"labels": labels, "values": values, "unit": defn.get("y_metric")}
