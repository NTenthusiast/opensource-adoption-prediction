# -*- coding: utf-8 -*-
"""
步骤二：从原始调查 CSV 构建「技术 × 年份」面板数据。

输出：
    data/processed/panel.csv           # 长表：year, tech, category, usage, desire, admiration
    data/processed/panel_wide.csv      # 宽表（便于人工查看）
    data/processed/lagged_panel.csv    # 含滞后特征的长表（供建模）

指标定义（与原始论文一致）：
    usage      = 使用人数 / 该领域有效受访者数
    desire     = 想用人数 / 该领域有效受访者数
    admiration = (既使用又想用人数) / 使用人数   # 使用者中的「满意想继续」比例
    desire_gap = desire - usage                  # 渴望缺口
"""
import os
import zipfile
import numpy as np
import pandas as pd

import config
from config import RAW_DIR, PROCESSED_DIR, YEARS, CATEGORY_COLUMNS
from utils import parse_multiselect, normalize_tech_name


def read_year_columns(year: int):
    """只读取某一年 CSV 中与四大领域相关的列，大幅降低内存与时间开销。

    返回 {category: (used_list, desire_list)}，其中 list 与行对齐（元素为 set[str]）。
    """
    path = os.path.join(RAW_DIR, f"so_survey_{year}.zip")
    with zipfile.ZipFile(path) as zf:
        # 收集本年度需要读取的所有列
        need = set()
        for cat in CATEGORY_COLUMNS:
            used_col, desire_col = config.resolve_columns(cat, year)
            need.add(used_col)
            need.add(desire_col)

        # 先读表头，确认需要的列确实存在（不同年份列略有差异）
        with zf.open("survey_results_public.csv") as fh:
            header = fh.readline().decode("utf-8-sig", errors="replace").strip().split(",")
        usecols = [c for c in header if c in need]

        df = pd.read_csv(
            zf.open("survey_results_public.csv"),
            usecols=usecols,
            dtype=str,
            low_memory=False,
        )

    result = {}
    for cat in CATEGORY_COLUMNS:
        used_col, desire_col = config.resolve_columns(cat, year)
        if used_col in df.columns and desire_col in df.columns:
            result[cat] = (
                parse_multiselect(df[used_col]),
                parse_multiselect(df[desire_col]),
            )
    return result


def compute_rates(year, category, used_list, desire_list):
    """统计某年某领域内每项技术的 usage / desire / admiration。

    分母为该领域「使用题」有效回答人数（即 used 列非空的人数），
    与 Stack Overflow 官方口径一致。
    """
    n_used = sum(1 for s in used_list if s)
    n_desire = sum(1 for s in desire_list if s)
    n_total = max(n_used, n_desire)
    if n_total == 0:
        return pd.DataFrame()

    used_count, desire_count, both_count = {}, {}, {}
    for su, sd in zip(used_list, desire_list):
        for t in su:
            used_count[normalize_tech_name(t)] = used_count.get(normalize_tech_name(t), 0) + 1
        for t in sd:
            desire_count[normalize_tech_name(t)] = desire_count.get(normalize_tech_name(t), 0) + 1
        for t in su & sd:
            both_count[normalize_tech_name(t)] = both_count.get(normalize_tech_name(t), 0) + 1

    techs = sorted(set(used_count) | set(desire_count))
    rows = []
    for t in techs:
        u = used_count.get(t, 0)
        d = desire_count.get(t, 0)
        rows.append({
            "year": year,
            "category": category,
            "tech": t,
            "usage": u / n_total,
            "desire": d / n_total,
            "admiration": (both_count.get(t, 0) / u) if u > 0 else np.nan,
        })
    return pd.DataFrame(rows)


def build_panel():
    """构建长表面板。"""
    frames = []
    for year in YEARS:
        print(f"[处理] {year} ...")
        year_data = read_year_columns(year)
        for cat, (used_list, desire_list) in year_data.items():
            df = compute_rates(year, cat, used_list, desire_list)
            if not df.empty:
                frames.append(df)
    panel = pd.concat(frames, ignore_index=True)
    panel["desire_gap"] = panel["desire"] - panel["usage"]
    panel = panel.sort_values(["tech", "year"]).reset_index(drop=True)
    return panel


def add_lags(panel: pd.DataFrame, lag_order: int = 3) -> pd.DataFrame:
    """为每个技术生成滞后特征 Usage(t-1..t-k)、Desire(t-1..t-k)、Admiration(t-1)。

    返回长表，仅保留具备完整当前值（usage）的样本。
    """
    panel = panel.sort_values(["tech", "year"]).copy()
    tech_groups = []
    for tech, g in panel.groupby("tech"):
        g = g.sort_values("year")
        for k in range(1, lag_order + 1):
            g[f"usage_lag{k}"] = g["usage"].shift(k)
            g[f"desire_lag{k}"] = g["desire"].shift(k)
            g[f"admiration_lag{k}"] = g["admiration"].shift(k)
        tech_groups.append(g)
    lagged = pd.concat(tech_groups, ignore_index=True)
    lagged = lagged.dropna(subset=["usage_lag1", "desire_lag1"]).reset_index(drop=True)
    return lagged


def main():
    panel = build_panel()
    panel.to_csv(os.path.join(PROCESSED_DIR, "panel.csv"), index=False, encoding="utf-8-sig")

    # 宽表（行=技术，列=年份×指标），便于查看
    wide = panel.pivot_table(index=["tech", "category"], columns="year",
                             values=["usage", "desire", "desire_gap"])
    wide.columns = [f"{v}_{y}" for v, y in wide.columns]
    wide.to_csv(os.path.join(PROCESSED_DIR, "panel_wide.csv"), encoding="utf-8-sig")

    lagged = add_lags(panel, lag_order=config.LAG_ORDER)
    lagged.to_csv(os.path.join(PROCESSED_DIR, "lagged_panel.csv"),
                  index=False, encoding="utf-8-sig")

    print(f"\n面板规模：{panel['tech'].nunique()} 项技术，{len(panel)} 条记录")
    print(f"年度覆盖：{sorted(panel['year'].unique())}")
    print(f"滞后样本（建模用）：{len(lagged)} 条")
    print(f"各领域技术数：\n{panel.groupby('category')['tech'].nunique().to_string()}")


if __name__ == "__main__":
    main()
