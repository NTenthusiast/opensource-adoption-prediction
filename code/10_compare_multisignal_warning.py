"""把主仓评论动量纳入动态预警，并与原问卷规则做同样本回测。

决策只用预警当年及以前的信息；零变化阈值在观察结果前固定。
结果仅用于筛选人工核查对象，不解释为衰退概率或因果效应。
"""
import importlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, f1_score, precision_score, recall_score

BASE = Path(__file__).resolve().parent
DATA = BASE / "data" / "processed"
OUT = BASE / "results" / "tables"
OUT.mkdir(parents=True, exist_ok=True)
add_warning = importlib.import_module("09_validate_multisignal_warning").add_warning


def prepare(so_panel=None, gh_yearly=None):
    if so_panel is None:
        so_panel = pd.read_csv(DATA / "panel.csv", encoding="utf-8-sig")
    if gh_yearly is None:
        gh_yearly = pd.read_csv(DATA / "github_comment_yearly.csv", encoding="utf-8-sig")
    so = add_warning(so_panel)
    gh = gh_yearly.copy()
    gh = gh.sort_values(["tech", "year"]).copy()
    so = so[so["tech"].isin(gh["tech"].unique())].copy()
    group = gh.groupby("tech", sort=False)
    gh["previous_comments"] = group["issue_pr_comments"].shift(1)
    gh["previous_year"] = group["year"].shift(1)
    gh["future_comments"] = group["issue_pr_comments"].shift(-1)
    gh["future_year"] = group["year"].shift(-1)
    gh["comment_log_change"] = np.log1p(gh["issue_pr_comments"]) - np.log1p(gh["previous_comments"])
    merged = so.merge(gh[["tech", "year", "repo", "issue_pr_comments", "previous_comments",
                          "previous_year", "future_comments", "future_year", "comment_log_change"]],
                      on=["tech", "year"], how="inner", validate="one_to_one")
    merged["so_history_ok"] = merged["year"] - merged["prev_year"] == 1
    merged["gh_history_ok"] = merged["year"] - merged["previous_year"] == 1
    merged["eligible"] = merged["so_history_ok"] & merged["gh_history_ok"]
    merged["so_alert"] = merged["warning"]
    merged["gh_alert"] = merged["gh_history_ok"] & merged["comment_log_change"].lt(0)
    merged["double_alert"] = merged["so_alert"] & merged["gh_alert"]
    merged["either_alert"] = merged["so_alert"] | merged["gh_alert"]
    merged["alert_score"] = merged["so_alert"].astype(int) + merged["gh_alert"].astype(int)
    # 使用率是影响规模维度；仅在同级警报内部排序，不把它解释为衰退概率。
    merged["review_priority"] = np.where(
        merged["eligible"], merged["alert_score"] * merged["usage"], np.nan)
    merged["future_so_ok"] = merged["next_year"] - merged["year"] == 1
    merged["future_gh_ok"] = merged["future_year"] - merged["year"] == 1
    merged["usage_down"] = merged["future_so_ok"] & merged["delta_usage"].lt(0)
    merged["comments_down"] = merged["future_gh_ok"] & (
        merged["future_comments"] < merged["issue_pr_comments"])
    merged["状态"] = np.select(
        [~merged["so_history_ok"], ~merged["gh_history_ok"],
         merged["double_alert"], merged["so_alert"], merged["gh_alert"]],
        ["问卷历史不足", "评论历史不足", "双源收缩", "问卷单源警报", "评论单源警报"],
        default="暂无收缩信号")
    return merged


def score_one(sample, predictor, outcome):
    y = sample[outcome].astype(bool)
    pred = sample[predictor].astype(bool)
    return {"样本": len(sample), "技术数": sample.tech.nunique(),
            "警报数": int(pred.sum()), "命中": int((pred & y).sum()),
            "误报": int((pred & ~y).sum()), "漏报": int((~pred & y).sum()),
            "精确率": precision_score(y, pred, zero_division=0),
            "召回率": recall_score(y, pred, zero_division=0),
            "平衡准确率": balanced_accuracy_score(y, pred) if y.nunique() == 2 else np.nan,
            "F1": f1_score(y, pred, zero_division=0)}


def main():
    merged = prepare()
    matched = merged[merged["eligible"]].copy()
    matched.to_csv(OUT / "multisignal_backtest_cases.csv", index=False, encoding="utf-8-sig")
    rows = []
    for outcome, ok, label in [
        ("usage_down", "future_so_ok", "下一年问卷使用率下降"),
        ("comments_down", "future_gh_ok", "下一年主仓评论量下降"),
    ]:
        sample = matched[matched[ok]].copy()
        for predictor, name in [
            ("so_alert", "原规则：问卷渴望缺口连续为负"),
            ("gh_alert", "评论规则：当年评论量较上年下降"),
            ("double_alert", "双源同时收缩：高优先级"),
            ("either_alert", "任一信号收缩：广覆盖"),
        ]:
            rows.append({"因变量": label, "规则": name,
                         **score_one(sample, predictor, outcome)})
    comparison = pd.DataFrame(rows)
    comparison.to_csv(OUT / "multisignal_backtest_comparison.csv", index=False, encoding="utf-8-sig")
    print(comparison.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    latest = merged[merged["year"] == merged["year"].max()].copy()
    latest = latest.sort_values(["alert_score", "review_priority"], ascending=False)
    latest[["tech", "repo", "year", "usage", "desire_gap", "admiration",
            "issue_pr_comments", "comment_log_change", "so_alert", "gh_alert",
            "so_history_ok", "gh_history_ok", "alert_score", "review_priority", "状态"]].to_csv(
                OUT / "multisignal_warning_v2_latest.csv", index=False, encoding="utf-8-sig")
    print("\n最新可用双源状态：")
    print(latest[["tech", "year", "usage", "so_alert", "gh_alert", "状态"]].to_string(index=False))

    coverage = merged.groupby("tech", as_index=False).agg(
        repo=("repo", "first"), 问卷匹配年份=("year", "nunique"),
        可评估警报年份=("eligible", "sum"),
        有下一年问卷结果=("future_so_ok", "sum"),
        有下一年评论结果=("future_gh_ok", "sum"))
    coverage.to_csv(OUT / "multisignal_coverage.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
