"""Biểu đồ dùng cho báo cáo (matplotlib, backend không giao diện)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ai_service.config import FIGURES_DIR


def _save(fig, name: str) -> str:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / name
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return f"figures/{name}"


def pred_vs_actual(y, p, title: str, name: str, unit: str = "phút") -> str:
    fig, ax = plt.subplots(figsize=(5.2, 5))
    ax.scatter(y, p, s=6, alpha=0.35)
    lim = [0, max(np.max(y), np.max(p)) * 1.05]
    ax.plot(lim, lim, "r--", lw=1)
    ax.set(xlabel=f"Thực tế ({unit})", ylabel=f"Dự đoán ({unit})", title=title, xlim=lim, ylim=lim)
    return _save(fig, name)


def residual_hist(y, p, title: str, name: str) -> str:
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    ax.hist(np.asarray(p) - np.asarray(y), bins=50, color="#4c78a8")
    ax.axvline(0, color="r", lw=1)
    ax.set(xlabel="Sai số (dự đoán − thực tế, phút)", ylabel="Số ca", title=title)
    return _save(fig, name)


def bar(labels, values, title: str, xlabel: str, name: str, color="#4c78a8", highlight: str | None = None) -> str:
    fig, ax = plt.subplots(figsize=(6.5, 0.45 * len(labels) + 1.2))
    cols = ["#e45756" if highlight and l == highlight else color for l in labels]
    ax.barh(labels, values, color=cols)
    ax.invert_yaxis()
    ax.set(xlabel=xlabel, title=title)
    for i, v in enumerate(values):
        ax.text(v, i, f" {v:.2f}", va="center", fontsize=8)
    return _save(fig, name)
