"""接续官方 2023—2025 年调查，沿用原项目的技术年度比例定义。"""
from pathlib import Path

import pandas as pd

from importlib import import_module

from utils import parse_multiselect


BASE = Path(__file__).resolve().parent
RAW = BASE / "data" / "raw"
PROCESSED = BASE / "data" / "processed"
build_panel = import_module("02_build_panel")

COLUMNS = {
    "Language": ("LanguageHaveWorkedWith", "LanguageWantToWorkWith"),
    "Database": ("DatabaseHaveWorkedWith", "DatabaseWantToWorkWith"),
    "Platform": ("PlatformHaveWorkedWith", "PlatformWantToWorkWith"),
    "Webframework": ("WebframeHaveWorkedWith", "WebframeWantToWorkWith"),
}
OFFICIAL_URL = (
    "https://github.com/StackExchange/Survey/blob/32a114542da67e3759479637343718502742adfd/packages/archive/{year}/results.csv"
)


def recent_year(year):
    path = RAW / f"so_survey_{year}.csv"
    if not path.exists():
        raise FileNotFoundError(f"缺少官方原始文件：{path}；来源：{OFFICIAL_URL.format(year=year)}")
    need = [name for pair in COLUMNS.values() for name in pair]
    frame = pd.read_csv(path, usecols=need, dtype=str, low_memory=False, encoding="utf-8-sig")
    frames = []
    coverage = []
    for category, (used, desire) in COLUMNS.items():
        used_values = parse_multiselect(frame[used])
        desire_values = parse_multiselect(frame[desire])
        coverage.append({"year": year, "category": category, "调查总回答数": len(frame),
                         "使用题有效回答数": sum(bool(v) for v in used_values),
                         "想用题有效回答数": sum(bool(v) for v in desire_values)})
        part = build_panel.compute_rates(year, category, used_values, desire_values)
        frames.append(part)
    return pd.concat(frames, ignore_index=True), pd.DataFrame(coverage)


def main():
    old = pd.read_csv(PROCESSED / "panel.csv", encoding="utf-8-sig")
    pieces = [recent_year(y) for y in (2023, 2024, 2025)]
    newer = pd.concat([piece[0] for piece in pieces], ignore_index=True)
    pd.concat([piece[1] for piece in pieces], ignore_index=True).to_csv(
        PROCESSED / "survey_coverage_recent.csv", index=False, encoding="utf-8-sig")
    newer["tech"] = newer["tech"].replace({"Neo4J": "Neo4j"})
    panel = pd.concat([old, newer], ignore_index=True)
    panel["desire_gap"] = panel["desire"] - panel["usage"]
    panel = panel.sort_values(["category", "tech", "year"]).reset_index(drop=True)
    if panel.duplicated(["category", "tech", "year"]).any():
        raise ValueError("技术、领域、年份存在重复，需先检查选项映射")
    path = PROCESSED / "panel_extended.csv"
    panel.to_csv(path, index=False, encoding="utf-8-sig")
    print("扩展调查面板：", panel.groupby("year").agg(技术数=("tech", "nunique"),
                                         记录数=("tech", "size")).to_string())
    print(f"已保存 {path}")


if __name__ == "__main__":
    main()
