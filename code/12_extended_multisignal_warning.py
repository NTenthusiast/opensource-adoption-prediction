"""在较近且更大的样本上，原样回测四种双源预警规则。"""
import importlib
from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parent
DATA = BASE / "data" / "processed"
OUT = BASE / "results" / "tables"
core = importlib.import_module("10_compare_multisignal_warning")
WINDOW = range(2022, 2025)  # 预警年；下一年问卷与完整评论均已公布
GH_REQUIRED = {2023, 2024, 2025}


def run(panel=None, comments=None):
    if panel is None:
        panel = pd.read_csv(DATA / "panel_extended.csv", encoding="utf-8-sig")
    if comments is None:
        comments = pd.read_csv(DATA / "github_comment_yearly.csv", encoding="utf-8-sig")
    complete = comments.groupby("tech")["year"].apply(
        lambda s: GH_REQUIRED.issubset(set(s.astype(int))))
    chosen = complete[complete].index
    comments = comments[comments.tech.isin(chosen)].copy()
    joined = core.prepare(panel, comments)
    sample_pool = joined[joined.year.isin(WINDOW) & joined.eligible].copy()
    if not len(sample_pool):
        raise ValueError("近期窗口没有可评估记录，请检查年度问卷与评论覆盖")
    sample_pool.to_csv(OUT / "multisignal_recent_cases.csv", index=False, encoding="utf-8-sig")

    rows = []
    by_year = []
    rules = [
        ("so_alert", "原规则：问卷渴望缺口连续为负"),
        ("gh_alert", "评论规则：当年评论量较上年下降"),
        ("double_alert", "双源同时收缩：高优先级"),
        ("either_alert", "任一信号收缩：广覆盖"),
    ]
    for outcome, ok, label in [
        ("usage_down", "future_so_ok", "下一年问卷使用率下降"),
        ("comments_down", "future_gh_ok", "下一年主仓评论量下降"),
    ]:
        sample = sample_pool[sample_pool[ok]].copy()
        for predictor, name in rules:
            rows.append({"因变量": label, "规则": name,
                         **core.score_one(sample, predictor, outcome)})
            for year, group in sample.groupby("year"):
                by_year.append({"因变量": label, "规则": name, "预警年": year,
                                **core.score_one(group, predictor, outcome)})
    comparison = pd.DataFrame(rows)
    comparison.to_csv(OUT / "multisignal_recent_comparison.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(by_year).to_csv(OUT / "multisignal_recent_by_year.csv", index=False,
                                 encoding="utf-8-sig")

    # 保留更早两届预警作为敏感性核对，避免合并结果遮盖下一届调查的整体上移。
    sensitivity = []
    for outcome, ok, label in [
        ("usage_down", "future_so_ok", "下一年问卷使用率下降"),
        ("comments_down", "future_gh_ok", "下一年主仓评论量下降"),
    ]:
        subset = sample_pool[(sample_pool.year <= 2023) & sample_pool[ok]]
        for predictor, name in rules:
            sensitivity.append({"因变量": label, "规则": name,
                                **core.score_one(subset, predictor, outcome)})
    pd.DataFrame(sensitivity).to_csv(OUT / "multisignal_recent_pre2025_comparison.csv",
                                     index=False, encoding="utf-8-sig")

    common = panel[panel.year.isin([2024, 2025])].pivot_table(
        index=["category", "tech"], columns="year", values="usage").dropna()
    common["使用率上升"] = common[2025] > common[2024]
    shift = common.groupby(level="category")["使用率上升"].agg(["sum", "count"])
    shift = shift.rename(columns={"sum": "上升技术数", "count": "共同技术数"})
    shift["上升比例"] = shift["上升技术数"] / shift["共同技术数"]
    shift.reset_index().to_csv(OUT / "multisignal_recent_survey_shift.csv", index=False,
                               encoding="utf-8-sig")

    coverage = sample_pool.groupby("tech").agg(
        仓库=("repo", "first"), 可评估预警年=("year", lambda x: ",".join(map(str, x))),
        问卷结果条数=("future_so_ok", "sum"), 评论结果条数=("future_gh_ok", "sum"))
    coverage.reset_index().to_csv(OUT / "multisignal_recent_coverage.csv", index=False,
                                  encoding="utf-8-sig")
    latest = joined[(joined.year == 2025) & joined.eligible].sort_values(
        ["alert_score", "review_priority"], ascending=False)
    latest[["tech", "category", "repo", "year", "usage", "desire_gap",
            "issue_pr_comments", "so_alert", "gh_alert", "alert_score", "状态"]].to_csv(
        OUT / "multisignal_recent_latest.csv", index=False, encoding="utf-8-sig")
    return comparison, coverage, latest


def main():
    comparison, coverage, latest = run()
    print("\n近期回测：")
    print(comparison.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print("\n技术数：", len(coverage), "；最新状态数：", len(latest))


if __name__ == "__main__":
    main()
