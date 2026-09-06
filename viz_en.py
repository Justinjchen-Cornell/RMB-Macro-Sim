# -*- coding: utf-8 -*-
"""
viz_en.py - English variants of key report charts (light research style)
========================================================================
Self-contained English twins of:
  plot_capital_waterfall_en / plot_capital_inflow_trends_en / plot_scenario_wall_en
Palette imported from visualize to stay consistent.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from visualize import (BG, PANEL, GRID, TEXT, MUTED, ACCENT_GOLD, ACCENT_RED,
                       ACCENT_GREEN, ACCENT_BLUE, setup_ax)

IND_EN = {"export_lowend": "Low-end mfg", "export_hightech": "High-tech exports",
          "domestic_consumption": "Consumer", "real_estate": "Property",
          "infrastructure": "Infrastructure", "new_energy": "New energy",
          "semiconductor": "Semiconductor", "commodity_metals": "Metals",
          "power_compute": "Compute/Power", "gold": "Gold",
          "bank_insurance": "Banks/Insurance"}


def plot_capital_waterfall_en(capital: dict, save_path: str):
    fig, ax = plt.subplots(figsize=(11, 6.2), facecolor=BG)
    setup_ax(ax)
    labels = ["Export loss", "Financing inflow", "Capital deepening", "Net benefit"]
    vals = [capital["export_loss"], capital["cumulative_inflow"],
            capital["deepening_gain"], capital["net_benefit"]]
    seg_bottoms, acc = [0.0], vals[0]
    for v in vals[1:-1]:
        seg_bottoms.append(acc if v >= 0 else acc + v)
        acc += v
    seg_bottoms.append(0.0)
    seg_heights = vals[:3] + [vals[3]]
    colors = [ACCENT_RED, ACCENT_GREEN, ACCENT_GREEN, ACCENT_GOLD]
    x = np.arange(4)
    ax.bar(x, seg_heights, bottom=seg_bottoms, width=0.58, color=colors, alpha=0.9)
    for i, (v, b) in enumerate(zip(vals, seg_bottoms)):
        ypos = b + v if v >= 0 else b
        off = 0.06 if v >= 0 else -0.06
        ax.text(x[i], ypos + off, "%+.2f T$" % v, ha="center",
                va="bottom" if v >= 0 else "top", fontsize=12, fontweight="bold",
                color=TEXT)
    ax.axhline(0, color="#94a3b8", lw=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11, color=TEXT)
    ax.set_ylabel("T$ (5-year cumulative)", color=TEXT)
    ax.set_title("Net benefit waterfall - RMB appreciation (5y, T$)", fontsize=14,
                 color=TEXT, fontweight="bold")
    ax.set_ylim(min(min(vals), -0.6), max(acc, 3.2) * 1.12)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, facecolor=BG)
    plt.close(fig)


def plot_capital_inflow_trends_en(capital: dict, save_path: str):
    by = capital["by_year"]
    years = list(range(1, len(by) + 1))
    fig, ax = plt.subplots(figsize=(11, 5.6), facecolor=BG)
    setup_ax(ax)
    ax.stackplot(years, by["equity"], by["bond"], by["fdi"],
                 labels=["A-share", "CN bonds", "FDI"],
                 colors=[ACCENT_GOLD, ACCENT_BLUE, ACCENT_GREEN], alpha=0.85)
    ax.plot(years, by["total"], color=TEXT, lw=2, marker="o", ms=5,
            label="Annual total")
    for xx, tt in zip(years, by["total"]):
        ax.annotate("%.2f" % tt, (xx, tt), textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=9, color=MUTED)
    ax.legend(facecolor=PANEL, labelcolor=TEXT, loc="upper left")
    ax.set_xlabel("Year", color=TEXT)
    ax.set_ylabel("Net inflow (T$)", color=TEXT)
    ax.set_title("Capital inflow into RMB assets by channel - annual, T$",
                 fontsize=13, color=TEXT)
    ax.set_xticks(years)
    ax.set_ylim(0, float(by["total"].max()) * 1.5)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, facecolor=BG)
    plt.close(fig)


def plot_scenario_wall_en(scenarios: dict, save_path: str, title: str = None):
    names = list(scenarios.keys())
    n = len(names)
    fig, axes = plt.subplots(n, 3, figsize=(15.5, 3.1 * n), facecolor=BG)
    if n == 1:
        axes = axes.reshape(1, -1)
    heads = ["USD/CNY path (median + 25-75%)", "Industry profit shock Y5",
             "Net benefit waterfall (5y, T$)"]
    for c, h in enumerate(heads):
        axes[0][c].set_title(h, fontsize=11.5, pad=10, color=TEXT)
    order = ["export_lowend", "export_hightech", "new_energy",
             "domestic_consumption", "real_estate", "infrastructure",
             "semiconductor", "commodity_metals", "power_compute",
             "bank_insurance", "gold"]
    for i, (name, r) in enumerate(scenarios.items()):
        ax = axes[i][0]
        fx = r["fx_path"]
        yrs = list(range(fx.shape[1]))
        med = np.median(fx, axis=0)
        lo = np.percentile(fx, 25, axis=0)
        hi = np.percentile(fx, 75, axis=0)
        ax.plot(yrs, med, color=ACCENT_BLUE, lw=2.2)
        ax.fill_between(yrs, lo, hi, color=ACCENT_BLUE, alpha=0.14)
        ax.set_ylim(float(med.min()) * 0.97, float(med.max()) * 1.03)
        ax.annotate("end %.2f" % med[-1], xy=(yrs[-1], med[-1]), xytext=(4, 4),
                    textcoords="offset points", fontsize=9, color=ACCENT_BLUE,
                    fontweight="bold")
        setup_ax(ax)
        ax = axes[i][1]
        fin = r["industry_profit"].iloc[-1]
        fin = fin.reindex([k for k in order if k in fin.index]).dropna()
        vals = fin.values
        cols = [ACCENT_RED if v < 0 else ACCENT_GREEN for v in vals]
        ax.barh(range(len(vals)), vals * 100, color=cols, alpha=0.88, height=0.62)
        ax.set_yticks(range(len(vals)))
        ax.set_yticklabels([IND_EN.get(k, k) for k in fin.index], fontsize=8.5,
                           color=TEXT)
        for bi, v in enumerate(vals):
            ax.text(v * 100 + (0.4 if v >= 0 else -0.4), bi, "%+.0f%%" % (v * 100),
                    va="center", ha="left" if v >= 0 else "right", fontsize=8,
                    color=MUTED)
        ax.axvline(0, color="#94a3b8", lw=0.8)
        ax.set_xlim(-40, 22)
        setup_ax(ax)
        ax = axes[i][2]
        cap = r["capital_inflow"]
        labels = ["Export loss", "Financing", "Deepening", "Net"]
        vw = [cap["export_loss"], cap["cumulative_inflow"],
              cap["deepening_gain"], cap["net_benefit"]]
        xs = np.arange(4)
        bottoms, acc = [0.0], vw[0]
        for v in vw[1:-1]:
            bottoms.append(acc)
            acc += v
        bottoms.append(0.0)
        cols_w = [ACCENT_RED, ACCENT_GREEN, ACCENT_GREEN, ACCENT_GOLD]
        ax.bar(xs, vw, bottom=bottoms, width=0.55, color=cols_w, alpha=0.9)
        for xi, v in enumerate(vw):
            yp = bottoms[xi] + (v if v >= 0 else 0) + 0.05
            ax.text(xi, yp, "%+.2f" % v, ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=9, fontweight="bold",
                    color=TEXT)
        ax.set_xticks(xs)
        ax.set_xticklabels(labels, fontsize=9, color=TEXT)
        ax.axhline(0, color="#94a3b8", lw=0.8)
        ax.set_ylim(min(min(vw), -0.8), 3.4)
        setup_ax(ax)
        fig.text(0.006, (n - i - 0.5) / n, name, rotation=90, va="center",
                 ha="center", fontsize=10.5, fontweight="bold", color=MUTED)
    if title:
        fig.suptitle(title, fontsize=14.5, fontweight="bold", color=TEXT, y=0.995)
    fig.tight_layout(rect=[0.025, 0.01, 1, 0.975 if title else 0.99])
    fig.savefig(save_path, dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print("  [en chart] %s" % save_path)
