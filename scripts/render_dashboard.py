from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yaml

LOG_PATH = Path("data/logs.jsonl")
DASHBOARD_PATH = Path("submission/evidence/12-incident-metric.png")


def load_logs() -> list[dict]:
    rows = []
    if not LOG_PATH.exists():
        return rows
    with LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def parse_ts(ts_str: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def aggregate_by_minute(rows: list[dict], field: str, condition=None):
    buckets = defaultdict(float)
    for r in rows:
        if condition and not condition(r):
            continue
        ts = parse_ts(r.get("ts", ""))
        if ts is None:
            continue
        key = ts.replace(second=0, microsecond=0)
        buckets[key] += float(r.get(field, 0) or 0)
    if not buckets:
        return [], []
    times = sorted(buckets.keys())
    values = [buckets[t] for t in times]
    return times, values


def aggregate_count_by_minute(rows: list[dict], condition=None):
    buckets = defaultdict(int)
    for r in rows:
        if condition and not condition(r):
            continue
        ts = parse_ts(r.get("ts", ""))
        if ts is None:
            continue
        key = ts.replace(second=0, microsecond=0)
        buckets[key] += 1
    if not buckets:
        return [], []
    times = sorted(buckets.keys())
    values = [buckets[t] for t in times]
    return times, values


def compute_percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    return float(np.percentile(values, p))


def build_dashboard(rows: list[dict], output_path: Path) -> None:
    response_rows = [r for r in rows if r.get("event") == "response_sent"]
    request_rows = [r for r in rows if r.get("event") == "request_received"]
    failed_rows = [r for r in rows if r.get("event") == "request_failed"]

    latencies = [r["latency_ms"] for r in response_rows if "latency_ms" in r]
    ttfts = [r["ttft_ms"] for r in response_rows if "ttft_ms" in r]
    costs = [r["cost_usd"] for r in response_rows if "cost_usd" in r]
    tokens_in = [r["tokens_in"] for r in response_rows if "tokens_in" in r]
    tokens_out = [r["tokens_out"] for r in response_rows if "tokens_out" in r]
    quality_scores = [r["quality_score"] for r in response_rows if "quality_score" in r]

    lat_p50 = compute_percentile(latencies, 50)
    lat_p95 = compute_percentile(latencies, 95)
    lat_p99 = compute_percentile(latencies, 99)
    ttft_p95 = compute_percentile(ttfts, 95)

    total_requests = len(request_rows)
    total_errors = len(failed_rows)
    error_rate = (total_errors / total_requests * 100) if total_requests else 0.0
    tool_success = [r.get("tool_success") for r in rows if r.get("tool_success") is not None]
    retrieval_success = sum(1 for v in tool_success if v is True)
    retrieval_total = len(tool_success)
    retrieval_rate = (retrieval_success / retrieval_total * 100) if retrieval_total else 0.0

    total_cost = sum(costs)
    total_tokens_in = sum(tokens_in)
    total_tokens_out = sum(tokens_out)
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    times_traffic, traffic_values = aggregate_count_by_minute(rows, lambda r: r.get("event") == "request_received")
    times_cost, cost_values = aggregate_by_minute(response_rows, "cost_usd")
    times_lat, lat_values = aggregate_by_minute(response_rows, "latency_ms")

    fig, axes = plt.subplots(3, 2, figsize=(14, 10))
    fig.suptitle("K4-L3B Day 13 Monitoring & LLMOps Dashboard", fontsize=14, fontweight="bold")

    # Panel 1: Latency
    ax = axes[0, 0]
    ax.bar(["P50", "P95", "P99", "TTFT P95"], [lat_p50, lat_p95, lat_p99, ttft_p95], color=["#4c78a8", "#f58518", "#e45756", "#72b7b2"])
    ax.axhline(y=3000, color="red", linestyle="--", label="SLO 3000ms")
    ax.set_title("Latency percentiles and TTFT")
    ax.set_ylabel("ms")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    # Panel 2: Traffic
    ax = axes[0, 1]
    if times_traffic:
        ax.plot(times_traffic, traffic_values, marker="o", color="#4c78a8")
    ax.set_title("Request traffic (per minute)")
    ax.set_ylabel("requests/min")
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    # Panel 3: Errors
    ax = axes[1, 0]
    ax.bar(["Error rate %", "Retrieval success %"], [error_rate, retrieval_rate], color=["#e45756", "#54a24b"])
    ax.axhline(y=2, color="red", linestyle="--", label="Error rate threshold 2%")
    ax.axhline(y=90, color="green", linestyle="--", label="Retrieval success threshold 90%")
    ax.set_title("Error rate and retrieval success")
    ax.set_ylabel("%")
    ax.set_ylim(0, 110)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    # Panel 4: Cost
    ax = axes[1, 1]
    if times_cost:
        ax.plot(times_cost, cost_values, marker="o", color="#f58518")
    ax.axhline(y=2.5, color="red", linestyle="--", label="Threshold 2.5 USD")
    ax.set_title("Cost over time")
    ax.set_ylabel("USD")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    # Panel 5: Tokens
    ax = axes[2, 0]
    ax.bar(["Input tokens", "Output tokens"], [total_tokens_in, total_tokens_out], color=["#4c78a8", "#f58518"])
    ax.axhline(y=50000, color="red", linestyle="--", label="Threshold 50000")
    ax.set_title("Input and output tokens")
    ax.set_ylabel("tokens")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    # Panel 6: Quality
    ax = axes[2, 1]
    ax.bar(["Avg quality score"], [avg_quality], color="#54a24b")
    ax.axhline(y=0.75, color="red", linestyle="--", label="Threshold 0.75")
    ax.set_title("Quality proxy")
    ax.set_ylabel("score")
    ax.set_ylim(0, 1.1)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close()


def main() -> None:
    rows = load_logs()
    if not rows:
        print("No logs found. Run load_test.py first.")
        return
    build_dashboard(rows, DASHBOARD_PATH)
    print(f"Dashboard saved to {DASHBOARD_PATH}")


if __name__ == "__main__":
    main()
