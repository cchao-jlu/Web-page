from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


def load_results(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def group_by_run(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        grouped.setdefault(item.get("run_name", "unnamed"), []).append(item)
    return grouped


def compute_metrics(group: list[dict[str, Any]]) -> dict[str, float]:
    scores = [g["score"] for g in group]
    lengths = [g["metrics"]["length"] for g in group]
    citations = [g["metrics"]["citations"] for g in group]
    sources = [g["metrics"]["source_count"] for g in group]

    def avg(vals):
        return round(sum(vals) / len(vals), 3) if vals else 0.0

    return {
        "avg_score": avg(scores),
        "avg_length": avg(lengths),
        "avg_citations": avg(citations),
        "avg_sources": avg(sources),
        "count": len(scores),
        "std_score": round(statistics.pstdev(scores), 3) if len(scores) > 1 else 0.0,
    }


def make_table(grouped: dict[str, list[dict[str, Any]]]) -> str:
    headers = ["Run", "Count", "Avg Score", "Std", "Avg Len", "Avg Citations", "Avg Sources"]
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for name, items in grouped.items():
        m = compute_metrics(items)
        lines.append(
            f"| {name} | {m['count']} | {m['avg_score']} | {m['std_score']} | {m['avg_length']} | {m['avg_citations']} | {m['avg_sources']} |"
        )
    return "\n".join(lines)

def make_latex_table(grouped: dict[str, list[dict[str, Any]]]) -> str:
    headers = ["Run", "Count", "AvgScore", "Std", "AvgLen", "AvgCite", "AvgSrc"]
    lines = [
        "\\begin{tabular}{lrrrrrr}",
        "\\toprule",
        " & ".join(headers) + " \\\\",
        "\\midrule",
    ]
    for name, items in grouped.items():
        m = compute_metrics(items)
        lines.append(
            f"{name} & {m['count']} & {m['avg_score']} & {m['std_score']} & {m['avg_length']} & {m['avg_citations']} & {m['avg_sources']} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    return "\n".join(lines)


def plot_scores(grouped: dict[str, list[dict[str, Any]]], output_dir: Path) -> Path:
    names = list(grouped.keys())
    scores = [compute_metrics(grouped[n])["avg_score"] for n in names]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(names, scores, color="#c06b2c")
    ax.set_ylabel("Avg Score")
    ax.set_title("Average Evaluation Score by Run")
    ax.set_ylim(0, max(scores) + 0.5 if scores else 1)
    ax.grid(axis="y", alpha=0.3)
    plt.xticks(rotation=20, ha="right")
    output = output_dir / "avg_scores.png"
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)
    return output


def plot_sources(grouped: dict[str, list[dict[str, Any]]], output_dir: Path) -> Path:
    names = list(grouped.keys())
    sources = [compute_metrics(grouped[n])["avg_sources"] for n in names]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(names, sources, marker="o", color="#2b7a6d")
    ax.set_ylabel("Avg Sources")
    ax.set_title("Average Source Count by Run")
    ax.grid(axis="y", alpha=0.3)
    plt.xticks(rotation=20, ha="right")
    output = output_dir / "avg_sources.png"
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)
    return output

def plot_radar(grouped: dict[str, list[dict[str, Any]]], output_dir: Path) -> Path:
    import numpy as np

    metrics = ["avg_score", "avg_length", "avg_citations", "avg_sources"]
    names = list(grouped.keys())
    values = [compute_metrics(grouped[n]) for n in names]

    # Normalize each metric by max to fit 0-1
    max_vals = {m: max(v[m] for v in values) or 1 for m in metrics}
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    for name, v in zip(names, values):
        data = [v[m] / max_vals[m] for m in metrics]
        data += data[:1]
        ax.plot(angles, data, label=name)
        ax.fill(angles, data, alpha=0.08)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([m.replace("avg_", "") for m in metrics])
    ax.set_yticklabels([])
    ax.set_title("Normalized Metrics Radar")
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1))
    output = output_dir / "radar_metrics.png"
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)
    return output

def plot_errorbars(grouped: dict[str, list[dict[str, Any]]], output_dir: Path) -> Path:
    names = list(grouped.keys())
    means = [compute_metrics(grouped[n])["avg_score"] for n in names]
    stds = [compute_metrics(grouped[n])["std_score"] for n in names]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.errorbar(names, means, yerr=stds, fmt="o", color="#1a7a74", ecolor="#888", capsize=4)
    ax.set_ylabel("Avg Score ± Std")
    ax.set_title("Score Variability by Run")
    ax.grid(axis="y", alpha=0.3)
    plt.xticks(rotation=20, ha="right")
    output = output_dir / "score_errorbars.png"
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)
    return output


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate experiment report table + plots")
    parser.add_argument("--input", required=True, help="results JSON path")
    parser.add_argument("--output", default="results/report.md")
    args = parser.parse_args()

    payload = load_results(args.input)
    grouped = group_by_run(payload.get("results", []))
    table = make_table(grouped)

    output_path = Path(args.output)
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    score_plot = plot_scores(grouped, output_dir)
    sources_plot = plot_sources(grouped, output_dir)
    radar_plot = plot_radar(grouped, output_dir)
    error_plot = plot_errorbars(grouped, output_dir)
    latex_table = make_latex_table(grouped)

    md = "\n".join(
        [
            "# Experiment Report",
            "",
            "## Summary Table",
            table,
            "",
            "## LaTeX Table",
            "```latex",
            latex_table,
            "```",
            "",
            "## Plots",
            f"![Average Scores]({score_plot.name})",
            "",
            f"![Average Sources]({sources_plot.name})",
            "",
            f"![Radar Metrics]({radar_plot.name})",
            "",
            f"![Score Error Bars]({error_plot.name})",
            "",
        ]
    )
    output_path.write_text(md, encoding="utf-8")
    print(f"Saved report to {output_path}")


if __name__ == "__main__":
    main()
