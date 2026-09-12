# -*- coding: utf-8 -*-
"""
步骤七（后续工作·长期）：构建「存量-增量-口碑」三维动态预警系统。

三维指标（均取最新年份）：
    存量（Stock）  = usage       使用率（用户基本盘）
    增量（Inflow） = desire_gap  渴望缺口（desire - usage，净流入/流出）
    口碑（Repute） = admiration  欣赏率（使用者中「满意想继续」的比例）

预警规则：
    - 渴望缺口连续 2 年为负  -> 「衰退预警」
    - 渴望缺口连续 2 年为正  -> 「增长信号」
    - 其余                  -> 「观察/稳定」
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import config
from config import WARNING_CONSECUTIVE_YEARS, TABLE_DIR
from utils import save_fig, PALETTE


def classify_tech(tech: str, g: pd.DataFrame):
    """对单个技术的时间序列分类。"""
    g = g.sort_values("year")
    gaps = g["desire_gap"].values
    last = g.iloc[-1]
    # 连续负/正（从最新年份往前数）
    def consec(vals, sign):
        k = 0
        for v in vals[::-1]:
            if sign == "neg" and v < 0:
                k += 1
            elif sign == "pos" and v > 0:
                k += 1
            else:
                break
        return k

    neg = consec(gaps, "neg")
    pos = consec(gaps, "pos")
    if neg >= WARNING_CONSECUTIVE_YEARS:
        status = "衰退预警"
    elif pos >= WARNING_CONSECUTIVE_YEARS:
        status = "增长信号"
    else:
        status = "观察/稳定"
    return pd.Series({
        "tech": tech, "category": last["category"],
        "usage": last["usage"], "desire_gap": last["desire_gap"],
        "admiration": last["admiration"], "consec_neg": neg,
        "status": status, "year": last["year"],
    })


def main():
    panel = pd.read_csv(os.path.join(config.PROCESSED_DIR, "panel.csv"))
    rows = pd.DataFrame([classify_tech(tech, g) for tech, g in panel.groupby("tech")])
    rows = rows.reset_index(drop=True)

    warn = rows[rows["status"] == "衰退预警"].sort_values("desire_gap")
    growth = rows[rows["status"] == "增长信号"].sort_values("desire_gap", ascending=False)
    print("=" * 72)
    print(f"【后续工作 ⑤】三维动态预警系统（数据年份截至 {rows['year'].max()}）")
    print(f"共 {len(rows)} 项技术：衰退预警 {len(warn)} 项 / 增长信号 {len(growth)} 项 "
          f"/ 观察稳定 {(rows['status']=='观察/稳定').sum()} 项")
    print("=" * 72)
    print("\n>>> 衰退预警技术（渴望缺口连续负，Top 15）：")
    print(warn[["tech", "usage", "desire_gap", "admiration", "consec_neg"]]
          .round(4).head(15).to_string(index=False))
    print("\n>>> 增长信号技术（渴望缺口连续正，Top 15）：")
    print(growth[["tech", "usage", "desire_gap", "admiration", "consec_neg"]]
          .round(4).head(15).to_string(index=False))

    rows.to_csv(os.path.join(TABLE_DIR, "early_warning_status.csv"),
                index=False, encoding="utf-8-sig")

    # ---------- 可视化：存量(横) × 增量(纵) × 口碑(颜色) ----------
    fig, ax = plt.subplots(figsize=(11, 7))
    color_map = {"衰退预警": PALETTE["red"], "增长信号": PALETTE["green"],
                 "观察/稳定": PALETTE["grey"]}
    for status, grp in rows.groupby("status"):
        ax.scatter(grp["usage"], grp["desire_gap"], s=40 + 60 * grp["admiration"].fillna(0),
                   c=color_map[status], alpha=0.75, edgecolor="white",
                   linewidth=0.5, label=status)
    # 标注代表性技术
    for _, r in pd.concat([warn.head(8), growth.head(8)]).iterrows():
        ax.annotate(r["tech"], (r["usage"], r["desire_gap"]),
                    fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("存量：使用率 usage（用户基本盘）")
    ax.set_ylabel("增量：渴望缺口 desire_gap（净流入/流出）")
    ax.set_title("「存量 × 增量 × 口碑」三维动态预警图（气泡大小=口碑 admiration）")
    ax.legend(loc="upper right")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    save_fig(fig, "07_early_warning")
    print(f"\n>>> 已保存图 results/figures/07_early_warning.png")
    return rows


if __name__ == "__main__":
    main()
