"""检查近期扩样回测的年份边界、记录唯一性与混淆矩阵守恒。"""
from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parent
TABLES = BASE / "results" / "tables"


def main():
    cases = pd.read_csv(TABLES / "multisignal_recent_cases.csv", encoding="utf-8-sig")
    results = pd.read_csv(TABLES / "multisignal_recent_comparison.csv", encoding="utf-8-sig")
    latest = pd.read_csv(TABLES / "multisignal_recent_latest.csv", encoding="utf-8-sig")
    assert set(cases.year).issubset({2022, 2023, 2024})
    assert not cases.duplicated(["tech", "year"]).any()
    assert ((cases.loc[cases.future_so_ok, "next_year"] -
             cases.loc[cases.future_so_ok, "year"]) == 1).all()
    assert ((cases.loc[cases.future_gh_ok, "future_year"] -
             cases.loc[cases.future_gh_ok, "year"]) == 1).all()
    assert (results["警报数"] == results["命中"] + results["误报"]).all()
    assert (results["样本"] >= results["命中"] + results["误报"] + results["漏报"]).all()
    assert (latest.year == 2025).all()
    print("近期扩样年份、去重和计数检查通过")


if __name__ == "__main__":
    main()
