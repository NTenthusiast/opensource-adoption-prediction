# -*- coding: utf-8 -*-
"""
步骤四（后续工作·短期②）：引入 SHAP 值，量化「渴望缺口」对单项技术预测的具体贡献。

原论文在随机森林中发现「时间窗口稀释效应」——渴望率的重要性会被多个历史
采纳率滞后项稀释。本脚本用 SHAP（TreeExplainer）对测试集逐样本分解预测，
得到：(1) 全局特征重要性；(2) 单项技术的逐特征归因，尤其量化「渴望缺口」
这一增量信号的贡献。

特征集：
    usage_lag1/2/3  历史惯性
    desire_lag1     意愿信号
    desire_gap_lag1 渴望缺口（desire - usage 的滞后值，即「净流入」信号）
    admiration_lag1 口碑信号
    category_*      领域虚拟变量
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit

import config
from config import TEST_YEAR, TABLE_DIR
from utils import save_fig, PALETTE, metrics, ensure_optional
shap = ensure_optional("shap")
if shap is None:
    import sys
    sys.exit(2)  # 退出码 2 = 缺依赖，run_all.py 会跳过并提示


FEATURES = ["usage_lag1", "usage_lag2", "usage_lag3",
            "desire_lag1", "desire_gap_lag1", "admiration_lag1"]
FEATURE_CN = {
    "usage_lag1": "历史惯性 t-1",
    "usage_lag2": "历史惯性 t-2",
    "usage_lag3": "历史惯性 t-3",
    "desire_lag1": "渴望率 t-1",
    "desire_gap_lag1": "渴望缺口 t-1",
    "admiration_lag1": "欣赏率 t-1",
}


def build_X(df):
    X = df[FEATURES].copy()
    for cat in ["Language", "Database", "Platform", "Webframework"]:
        X[f"category_{cat}"] = (df["category"] == cat).astype(float)
    return X


def main():
    df = pd.read_csv(os.path.join(config.PROCESSED_DIR, "lagged_panel.csv"))
    df = df.dropna(subset=["usage", "usage_lag1", "desire_lag1"]).copy()
    df["desire_gap_lag1"] = df["desire_lag1"] - df["usage_lag1"]

    train = df[df["year"] < TEST_YEAR].reset_index(drop=True)
    test = df[df["year"] == TEST_YEAR].reset_index(drop=True)

    X_train, y_train = build_X(train), train["usage"].values
    X_test, y_test = build_X(test), test["usage"].values

    # 时序交叉验证确定 n_estimators / max_depth
    tscv = TimeSeriesSplit(n_splits=3)
    best, best_score = None, -1e9
    for ne in [100, 200, 400]:
        for md in [3, 5, 7]:
            r2s = []
            for tr, va in tscv.split(X_train):
                m = RandomForestRegressor(n_estimators=ne, max_depth=md,
                                          random_state=config.RANDOM_STATE, n_jobs=-1)
                m.fit(X_train.iloc[tr], y_train[tr])
                r2s.append(metrics(y_train[va], m.predict(X_train.iloc[va]))["R2"])
            score = float(np.mean(r2s))
            if score > best_score:
                best_score, best = score, (ne, md)
    ne, md = best
    print(f"[SHAP] 最优参数 n_estimators={ne}, max_depth={md} (CV R²={best_score:.4f})")

    rf = RandomForestRegressor(n_estimators=ne, max_depth=md,
                               random_state=config.RANDOM_STATE, n_jobs=-1)
    rf.fit(X_train, y_train)
    pred = rf.predict(X_test)
    m = metrics(y_test, pred)
    print(f"[SHAP] 测试集({TEST_YEAR})：R²={m['R2']:.4f}  RMSE={m['RMSE']:.4f}  MAE={m['MAE']:.4f}")

    # ---------- SHAP ----------
    explainer = shap.TreeExplainer(rf)
    shap_values = explainer.shap_values(X_test)
    if isinstance(shap_values, list):
        shap_values = shap_values[0]  # 部分版本返回 list
    shap_values = np.asarray(shap_values)

    # 全局特征重要性（mean |SHAP|）
    importance = pd.DataFrame({
        "feature": X_test.columns,
        "mean_abs_shap": np.abs(shap_values).mean(axis=0),
    }).sort_values("mean_abs_shap", ascending=False)
    importance["feature_cn"] = importance["feature"].map(
        lambda f: FEATURE_CN.get(f, f))
    importance.to_csv(os.path.join(TABLE_DIR, "shap_importance.csv"),
                      index=False, encoding="utf-8-sig")
    print("\n[SHAP] 全局特征重要性（mean |SHAP|）：")
    print(importance[["feature_cn", "mean_abs_shap"]].round(5).to_string(index=False))

    # 渴望缺口类信号合计占比
    gap_share = (importance.loc[importance["feature"].str.contains("desire_gap|desire_lag"),
                                "mean_abs_shap"].sum()
                 / importance["mean_abs_shap"].sum())
    print(f"\n[SHAP] 「意愿/缺口」类特征合计 SHAP 占比 = {gap_share:.2%}")

    # ---------- 可视化 1：全局重要性柱状图 ----------
    fig, ax = plt.subplots(figsize=(8, 5))
    imp = importance.sort_values("mean_abs_shap")
    colors = [PALETTE["orange"] if "gap" in f or "desire" in f else PALETTE["blue"]
              for f in imp["feature"]]
    ax.barh(imp["feature_cn"], imp["mean_abs_shap"], color=colors)
    ax.set_xlabel("mean |SHAP value|")
    ax.set_title(f"SHAP 全局特征重要性（测试集 {TEST_YEAR}）")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    save_fig(fig, "04_shap_importance")

    # ---------- 可视化 2：单项技术归因（选代表性技术） ----------
    # 在测试集上找到 Rust / JavaScript / Python / Go 等代表技术
    focus_techs = ["Rust", "JavaScript", "Python", "Go", "PostgreSQL", "Docker"]
    rows = []
    for i in range(len(test)):
        tech = test.iloc[i]["tech"]
        if tech in focus_techs:
            row = {"技术": tech}
            for j, f in enumerate(X_test.columns):
                row[FEATURE_CN.get(f, f)] = shap_values[i, j]
            rows.append(row)
    if rows:
        tech_shap = pd.DataFrame(rows).drop_duplicates("技术")
        tech_shap.to_csv(os.path.join(TABLE_DIR, "shap_by_tech.csv"),
                         index=False, encoding="utf-8-sig")
        print("\n[SHAP] 代表技术的逐特征 SHAP 贡献（>0 推高使用率，<0 拉低使用率）：")
        print(tech_shap.round(4).to_string(index=False))

        fig, ax = plt.subplots(figsize=(9, 5))
        plot_df = tech_shap.set_index("技术")
        plot_df = plot_df.reindex([c for c in plot_df.columns])
        plot_df.T.plot(kind="bar", ax=ax, width=0.8)
        ax.axhline(0, color="black", lw=0.8)
        ax.set_ylabel("SHAP 贡献")
        ax.set_title("代表技术：逐特征 SHAP 归因（渴望缺口贡献可见）")
        ax.legend(title="技术", ncol=2)
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        save_fig(fig, "04_shap_by_tech")

    return importance, tech_shap


if __name__ == "__main__":
    main()
