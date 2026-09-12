# -*- coding: utf-8 -*-
"""
步骤三（后续工作·短期①）：用真实调查数据验证「采纳惯性 β1」与「渴望转化率 β2」。

原论文基于合规模拟数据得到 β1≈0.80、β2≈0.23（R²=0.989），但这两个值是
在模拟时「内置」的。本脚本改用 Stack Overflow 2018–2022 真实面板数据，
重新估计先行指标回归：

    Usage(t) = β0 + β1·Usage(t-1) + β2·Desire(t-1)

并回答：真实数据中 β1≈0.80、β2≈0.23 是否仍然成立？
"""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt

import config
from config import SIM_BETA1, SIM_BETA2, TABLE_DIR
from utils import save_fig, PALETTE


def load_lagged():
    df = pd.read_csv(os.path.join(config.PROCESSED_DIR, "lagged_panel.csv"))
    df = df.dropna(subset=["usage", "usage_lag1", "desire_lag1"]).reset_index(drop=True)
    return df


def ols(df, y="usage", xs=("usage_lag1", "desire_lag1"), intercept=True):
    X = df[list(xs)].copy()
    if intercept:
        X = sm.add_constant(X)
    model = sm.OLS(df[y], X).fit()
    return model


def main():
    df = load_lagged()

    # ---------- 1. 全样本回归 ----------
    m = ols(df)
    print("=" * 72)
    print("【后续工作 ①】真实数据验证先行指标回归")
    print(f"样本：{len(df)} 条（{df['tech'].nunique()} 项技术，{sorted(df['year'].unique())} 年）")
    print("=" * 72)
    print(m.summary2().tables[1].round(4).to_string())

    b1, b2 = m.params["usage_lag1"], m.params["desire_lag1"]
    r2 = m.rsquared
    print(f"\n>>> 真实数据：β1(采纳惯性) = {b1:.4f}    β2(渴望转化率) = {b2:.4f}    R² = {r2:.4f}")
    print(f">>> 模拟设定：β1 = {SIM_BETA1}          β2 = {SIM_BETA2}")
    print(f">>> 偏差：β1 偏差 {b1 - SIM_BETA1:+.4f}（{100*(b1-SIM_BETA1)/SIM_BETA1:+.2f}%），"
          f"β2 偏差 {b2 - SIM_BETA2:+.4f}（{100*(b2-SIM_BETA2)/SIM_BETA2:+.2f}%）")

    # ---------- 2. 分领域异质性 ----------
    print("\n【分领域异质性】")
    domain_rows = []
    for cat, g in df.groupby("category"):
        mm = ols(g)
        domain_rows.append({
            "领域": config.CATEGORY_CN.get(cat, cat),
            "β1": mm.params["usage_lag1"], "β2": mm.params["desire_lag1"],
            "R²": mm.rsquared, "N": len(g),
        })
    domain_df = pd.DataFrame(domain_rows)
    print(domain_df.round(4).to_string(index=False))
    domain_df.to_csv(os.path.join(TABLE_DIR, "regression_by_domain.csv"),
                     index=False, encoding="utf-8-sig")

    # ---------- 3. 稳健性：加入年份固定效应 ----------
    print("\n【稳健性：年份固定效应】")
    m_fe = ols(df, xs=("usage_lag1", "desire_lag1"), intercept=False)
    # 手工构造年份虚拟变量
    X = df[["usage_lag1", "desire_lag1"]].copy()
    yr_dummies = pd.get_dummies(df["year"], prefix="yr", drop_first=True).astype(float)
    X = pd.concat([yr_dummies, X], axis=1)
    X = sm.add_constant(X)
    m_fe = sm.OLS(df["usage"], X).fit()
    print(f"  β1 = {m_fe.params['usage_lag1']:.4f}  β2 = {m_fe.params['desire_lag1']:.4f}  "
          f"R² = {m_fe.rsquared:.4f}")

    # ---------- 4. 汇总表 ----------
    summary = pd.DataFrame({
        "参数": ["采纳惯性 β1", "渴望转化率 β2", "R²"],
        "模拟设定": [SIM_BETA1, SIM_BETA2, 0.989],
        "真实数据估计": [b1, b2, r2],
        "偏差": [b1 - SIM_BETA1, b2 - SIM_BETA2, r2 - 0.989],
    })
    summary.to_csv(os.path.join(TABLE_DIR, "regression_validation.csv"),
                   index=False, encoding="utf-8-sig")
    print("\n>>> 已保存结果到 results/tables/regression_validation.csv")

    # ---------- 5. 可视化 ----------
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

    # (a) 实际 vs 预测散点
    y = df["usage"].values
    yhat = m.predict(sm.add_constant(df[["usage_lag1", "desire_lag1"]]))
    ax = axes[0]
    ax.scatter(y, yhat, s=18, alpha=0.55, color=PALETTE["blue"], edgecolor="white", linewidth=0.4)
    lim = [0, max(y.max(), yhat.max()) * 1.05]
    ax.plot(lim, lim, "--", color=PALETTE["red"], lw=1.2, label="y = x")
    ax.set_xlabel("实际使用率 Usage(t)")
    ax.set_ylabel(r"预测使用率 $\hat{U}$sage(t)")
    ax.set_title(f"真实数据拟合 (R²={r2:.3f})")
    ax.legend(); ax.grid(alpha=0.25)

    # (b) 真实 vs 模拟参数对比
    ax = axes[1]
    labels = ["采纳惯性 β1", "渴望转化率 β2"]
    sim_vals = [SIM_BETA1, SIM_BETA2]
    real_vals = [b1, b2]
    x = np.arange(len(labels))
    w = 0.34
    ax.bar(x - w/2, sim_vals, w, label="模拟设定", color=PALETTE["grey"], alpha=0.85)
    ax.bar(x + w/2, real_vals, w, label="真实数据", color=PALETTE["blue"])
    for xi, (sv, rv) in zip(x, zip(sim_vals, real_vals)):
        ax.text(xi - w/2, sv + 0.01, f"{sv:.2f}", ha="center", fontsize=10)
        ax.text(xi + w/2, rv + 0.01, f"{rv:.2f}", ha="center", fontsize=10, color=PALETTE["blue"])
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.0); ax.set_ylabel("系数值")
    ax.set_title("真实数据 vs 模拟设定：两个核心行为参数")
    ax.legend(); ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()
    path = save_fig(fig, "03_regression_validation")
    print(f">>> 已保存图 {path}")
    return b1, b2, r2


if __name__ == "__main__":
    main()
