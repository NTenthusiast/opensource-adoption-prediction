# -*- coding: utf-8 -*-
"""
步骤五（后续工作·中期①）：将「技术迁移网络」的 PageRank / 社区划分等图特征
纳入随机森林，验证是否能进一步提升预测精度。

思路：
    1. 用训练年份（< TEST_YEAR）的受访者级数据构建技术「共现网络」——
       两个技术若常被同一开发者同时使用，则它们之间有一条加权边（即
       「迁移/邻近」关系）。
    2. 计算节点级图特征：PageRank、加权度、度中心性、Louvain 社区标签。
    3. 将这些静态图特征并入基准特征，对比随机森林「加图特征 vs 不加」的
       测试集 R² / RMSE。
"""
import os
import itertools
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit

import config
from config import TEST_YEAR, TABLE_DIR
from utils import save_fig, PALETTE, metrics, ensure_optional
nx = ensure_optional("networkx")
if nx is None:
    import sys
    sys.exit(2)  # 退出码 2 = 缺依赖，run_all.py 会跳过并提示
import networkx.algorithms.community as nx_comm
import importlib
read_year_columns = importlib.import_module("02_build_panel").read_year_columns

BASE_FEATURES = ["usage_lag1", "usage_lag2", "usage_lag3",
                 "desire_lag1", "admiration_lag1"]


def build_cooccurrence(years):
    """构建技术共现计数（跨四大领域、按受访者求并集后统计两两共现）。"""
    pair_counter = Counter()
    single_counter = Counter()
    for year in years:
        print(f"  [共现] 处理 {year} ...")
        year_data = read_year_columns(year)
        # 每个受访者：该年四大领域「使用」技术的并集
        per_respondent = []
        used_lists = [year_data[c][0] for c in year_data]
        n = min(len(u) for u in used_lists)
        for i in range(n):
            union = set()
            for u in used_lists:
                union |= u[i]
            union = {t for t in union if t}
            per_respondent.append(union)
            for t in union:
                single_counter[t] += 1
        for union in per_respondent:
            for a, b in itertools.combinations(sorted(union), 2):
                pair_counter[(a, b)] += 1
    return pair_counter, single_counter


def compute_graph_features(pair_counter, single_counter, min_co=10):
    """由共现计数构建网络，计算 PageRank / 度 / 社区等节点特征。"""
    G = nx.Graph()
    for (a, b), w in pair_counter.items():
        if w >= min_co:
            G.add_edge(a, b, weight=w)
    # 只保留出现次数足够的节点
    for t, c in list(single_counter.items()):
        if c >= min_co and t not in G:
            G.add_node(t)

    print(f"  [图] 节点数={G.number_of_nodes()}, 边数={G.number_of_edges()}")

    pr = nx.pagerank(G, weight="weight")
    deg = dict(G.degree())
    wdeg = dict(G.degree(weight="weight"))

    # Louvain 社区划分
    try:
        comms = nx_comm.louvain_communities(G, weight="weight", seed=config.RANDOM_STATE)
        comm_label = {}
        for ci, members in enumerate(comms):
            for t in members:
                comm_label[t] = ci
    except Exception:
        comm_label = {t: 0 for t in G.nodes()}

    feat = pd.DataFrame({
        "tech": list(G.nodes()),
        "pagerank": [pr.get(t, 0.0) for t in G.nodes()],
        "degree": [deg.get(t, 0) for t in G.nodes()],
        "weighted_degree": [wdeg.get(t, 0.0) for t in G.nodes()],
        "community": [comm_label.get(t, 0) for t in G.nodes()],
    })
    # 社区编号转为 one-hot（社区数不定，直接用数值亦可，这里保留数值 + one-hot）
    n_comm = feat["community"].nunique()
    for c in range(n_comm):
        feat[f"comm_{c}"] = (feat["community"] == c).astype(float)
    return G, feat


def main():
    df = pd.read_csv(os.path.join(config.PROCESSED_DIR, "lagged_panel.csv"))
    df = df.dropna(subset=["usage", "usage_lag1", "desire_lag1"]).copy()

    train_years = [y for y in config.YEARS if y < TEST_YEAR]
    print(f"[图特征] 训练年份={train_years}（测试年份={TEST_YEAR}）")
    pair_counter, single_counter = build_cooccurrence(train_years)
    G, graph_feat = compute_graph_features(pair_counter, single_counter, min_co=10)

    # 合并图特征（按 tech 对齐）
    df = df.merge(graph_feat, on="tech", how="left")
    graph_cols = ["pagerank", "degree", "weighted_degree", "community"] + \
                 [c for c in graph_feat.columns if c.startswith("comm_")]
    for c in graph_cols:
        df[c] = df[c].fillna(0.0)

    # 领域虚拟变量
    for cat in ["Language", "Database", "Platform", "Webframework"]:
        df[f"category_{cat}"] = (df["category"] == cat).astype(float)
    cat_cols = [f"category_{c}" for c in ["Language", "Database", "Platform", "Webframework"]]

    train = df[df["year"] < TEST_YEAR].reset_index(drop=True)
    test = df[df["year"] == TEST_YEAR].reset_index(drop=True)

    def run_rf(features, tag):
        X_tr, y_tr = train[features], train["usage"].values
        X_te, y_te = test[features], test["usage"].values
        tscv = TimeSeriesSplit(n_splits=3)
        best, best_score = None, -1e9
        for ne in [100, 200, 400]:
            for md in [3, 5, 7]:
                r2s = []
                for tr, va in tscv.split(X_tr):
                    m = RandomForestRegressor(n_estimators=ne, max_depth=md,
                                              random_state=config.RANDOM_STATE, n_jobs=-1)
                    m.fit(X_tr.iloc[tr], y_tr[tr])
                    r2s.append(metrics(y_tr[va], m.predict(X_tr.iloc[va]))["R2"])
                if np.mean(r2s) > best_score:
                    best_score, best = np.mean(r2s), (ne, md)
        m = RandomForestRegressor(n_estimators=best[0], max_depth=best[1],
                                  random_state=config.RANDOM_STATE, n_jobs=-1)
        m.fit(X_tr, y_tr)
        pred = m.predict(X_te)
        res = metrics(y_te, pred)
        imp = pd.Series(m.feature_importances_, index=features).sort_values(ascending=False)
        print(f"\n[{tag}] 最优参数 n={best[0]}, depth={best[1]}  ->  "
              f"测试集 R²={res['R2']:.4f}, RMSE={res['RMSE']:.4f}, MAE={res['MAE']:.4f}")
        return res, imp

    base_cols = BASE_FEATURES + cat_cols
    res_base, imp_base = run_rf(base_cols, "基准（无图特征）")
    res_graph, imp_graph = run_rf(base_cols + graph_cols, "加图特征")

    comparison = pd.DataFrame({
        "模型": ["基准（无图特征）", "加图特征（PageRank/社区/度）"],
        "R²": [res_base["R2"], res_graph["R2"]],
        "RMSE": [res_base["RMSE"], res_graph["RMSE"]],
        "MAE": [res_base["MAE"], res_graph["MAE"]],
    })
    comparison.to_csv(os.path.join(TABLE_DIR, "graph_feature_comparison.csv"),
                      index=False, encoding="utf-8-sig")
    print("\n>>> 对比结果：")
    print(comparison.round(4).to_string(index=False))
    print(f"\n>>> 图特征带来的 R² 变化 = {res_graph['R2'] - res_base['R2']:+.4f}")

    # ---------- 可视化：网络 + 对比 ----------
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    # (a) 迁移网络（按社区着色，节点大小 = PageRank）
    ax = axes[0]
    pos = nx.spring_layout(G, seed=config.RANDOM_STATE, k=0.7)
    pr = nx.pagerank(G, weight="weight")
    comms = nx_comm.louvain_communities(G, weight="weight", seed=config.RANDOM_STATE)
    color_map = {}
    palette = list(PALETTE.values())
    for ci, members in enumerate(comms):
        for t in members:
            color_map[t] = palette[ci % len(palette)]
    node_color = [color_map.get(n, PALETTE["grey"]) for n in G.nodes()]
    node_size = [2000 * pr.get(n, 0) / max(pr.values()) + 40 for n in G.nodes()]
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.12, width=0.5)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_color, node_size=node_size, alpha=0.85)
    labels = {n: n for n in G.nodes() if pr.get(n, 0) > np.percentile(list(pr.values()), 80)}
    nx.draw_networkx_labels(G, pos, labels, ax=ax, font_size=7)
    ax.set_title(f"技术迁移网络（节点大小=PageRank，颜色=社区，{G.number_of_nodes()} 节点）")
    ax.axis("off")

    # (b) 加图特征 vs 基准
    ax = axes[1]
    labels = ["R²", "RMSE"]
    base_vals = [res_base["R2"], res_base["RMSE"]]
    graph_vals = [res_graph["R2"], res_graph["RMSE"]]
    x = np.arange(2); w = 0.34
    ax.bar(x - w/2, base_vals, w, label="基准", color=PALETTE["grey"])
    ax.bar(x + w/2, graph_vals, w, label="加图特征", color=PALETTE["blue"])
    for xi, (bv, gv) in zip(x, zip(base_vals, graph_vals)):
        ax.text(xi - w/2, bv + 0.001, f"{bv:.4f}", ha="center", fontsize=9)
        ax.text(xi + w/2, gv + 0.001, f"{gv:.4f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_title(f"图特征对预测精度的提升（R² 变化 {res_graph['R2']-res_base['R2']:+.4f}）")
    ax.legend(); ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save_fig(fig, "05_graph_features")
    print(f">>> 已保存图 results/figures/05_graph_features.png")

    return comparison, imp_graph


if __name__ == "__main__":
    main()
