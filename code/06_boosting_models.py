# -*- coding: utf-8 -*-
"""
步骤六（后续工作·中期②）：横向对比随机森林 / XGBoost / LightGBM 三种集成模型。

在同一套特征、同一套时序切分下，对三种模型做网格搜索（配合 TimeSeriesSplit），
报告测试集 R² / RMSE / MAE，并给出特征重要性对比。
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
xgb = ensure_optional("xgboost")
lgbm = ensure_optional("lightgbm")
if xgb is None or lgbm is None:
    import sys
    sys.exit(2)  # 退出码 2 = 缺依赖，run_all.py 会跳过并提示


FEATURES = ["usage_lag1", "usage_lag2", "usage_lag3",
            "desire_lag1", "admiration_lag1"]


def build_features(df):
    X = df[FEATURES].copy()
    for cat in ["Language", "Database", "Platform", "Webframework"]:
        X[f"category_{cat}"] = (df["category"] == cat).astype(float)
    return X


def ts_grid_search(model_factory, param_grid, X, y, tscv):
    """对参数网格做时序交叉验证，返回最优参数与最优 CV R²。"""
    best, best_score = None, -1e9
    import itertools
    keys = list(param_grid.keys())
    for vals in itertools.product(*param_grid.values()):
        params = dict(zip(keys, vals))
        r2s = []
        for tr, va in tscv.split(X):
            m = model_factory(**params)
            m.fit(X.iloc[tr], y[tr])
            r2s.append(metrics(y[va], m.predict(X.iloc[va]))["R2"])
        score = float(np.mean(r2s))
        if score > best_score:
            best_score, best = score, params
    return best, best_score


def main():
    df = pd.read_csv(os.path.join(config.PROCESSED_DIR, "lagged_panel.csv"))
    df = df.dropna(subset=["usage", "usage_lag1", "desire_lag1"]).copy()

    train = df[df["year"] < TEST_YEAR].reset_index(drop=True)
    test = df[df["year"] == TEST_YEAR].reset_index(drop=True)
    X_train, y_train = build_features(train), train["usage"].values
    X_test, y_test = build_features(test), test["usage"].values
    tscv = TimeSeriesSplit(n_splits=3)

    models = {
        "随机森林 RF": {
            "factory": lambda **p: RandomForestRegressor(random_state=config.RANDOM_STATE, n_jobs=-1, **p),
            "grid": {"n_estimators": [200, 400], "max_depth": [3, 5, 7]},
        },
        "XGBoost": {
            "factory": lambda **p: xgb.XGBRegressor(
                random_state=config.RANDOM_STATE, n_jobs=-1,
                objective="reg:squarederror", eval_metric="rmse", **p),
            "grid": {"n_estimators": [200, 400], "max_depth": [3, 5, 7],
                     "learning_rate": [0.05, 0.1]},
        },
        "LightGBM": {
            "factory": lambda **p: lgbm.LGBMRegressor(
                random_state=config.RANDOM_STATE, n_jobs=-1,
                verbosity=-1, **p),
            "grid": {"n_estimators": [200, 400], "max_depth": [3, 5, 7],
                     "learning_rate": [0.05, 0.1]},
        },
    }

    results, importances = [], {}
    for name, spec in models.items():
        print(f"\n[调参] {name} ...")
        best_params, cv_r2 = ts_grid_search(spec["factory"], spec["grid"],
                                            X_train, y_train, tscv)
        m = spec["factory"](**best_params)
        m.fit(X_train, y_train)
        pred = m.predict(X_test)
        res = metrics(y_test, pred)
        res.update({"模型": name, "CV_R2": cv_r2, "最优参数": str(best_params)})
        results.append(res)
        print(f"  {name}: 最优参数={best_params}  测试集 R²={res['R2']:.4f}, "
              f"RMSE={res['RMSE']:.4f}, MAE={res['MAE']:.4f}")
        try:
            imp = m.feature_importances_
            importances[name] = pd.Series(imp, index=X_train.columns)
        except Exception:
            pass

    result_df = pd.DataFrame(results)[["模型", "R2", "RMSE", "MAE", "CV_R2"]]
    result_df.to_csv(os.path.join(TABLE_DIR, "boosting_comparison.csv"),
                     index=False, encoding="utf-8-sig")
    print("\n>>> 三模型横向对比：")
    print(result_df.round(4).to_string(index=False))

    # ---------- 可视化 ----------
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

    ax = axes[0]
    x = np.arange(len(result_df)); w = 0.55
    ax.bar(x, result_df["R2"], w, color=[PALETTE["blue"], PALETTE["orange"], PALETTE["green"]])
    for xi, r2 in zip(x, result_df["R2"]):
        ax.text(xi, r2 + 0.002, f"{r2:.4f}", ha="center", fontsize=11)
    ax.set_xticks(x); ax.set_xticklabels(result_df["模型"])
    ax.set_ylim(0, 1.05); ax.set_ylabel("测试集 R²")
    ax.set_title(f"三种集成模型预测精度对比（测试集 {TEST_YEAR}）")
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1]
    imp_df = pd.DataFrame(importances).fillna(0)
    imp_df.columns = [c.replace("XGBoost", "XGBoost").replace("LightGBM", "LightGBM") for c in imp_df.columns]
    imp_df.plot(kind="bar", ax=ax, width=0.8)
    ax.set_ylabel("特征重要性")
    ax.set_title("特征重要性对比")
    ax.legend(title="模型")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save_fig(fig, "06_boosting_comparison")
    print(f">>> 已保存图 results/figures/06_boosting_comparison.png")

    return result_df


if __name__ == "__main__":
    main()
