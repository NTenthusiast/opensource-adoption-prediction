"""前瞻验证调查预警，并以 GitHub 评论量作为独立结果变量。

全部阈值沿用旧规则（渴望缺口连续两年为负），没有按测试结果调参。
调查指标是不同受访者的重复横截面；评论量是单一主仓的参与量代理。
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, precision_score, recall_score

BASE = Path(__file__).resolve().parent
DATA = BASE / "data" / "processed"
OUT = BASE / "results" / "tables"
OUT.mkdir(parents=True, exist_ok=True)


def add_warning(panel):
    panel = panel.sort_values(["category", "tech", "year"]).copy()
    keys = ["category", "tech"]
    group = panel.groupby(keys, sort=False)
    panel["prev_gap"] = group["desire_gap"].shift(1)
    panel["prev_year"] = group["year"].shift(1)
    panel["warning"] = ((panel["year"] - panel["prev_year"] == 1)
                        & (panel["desire_gap"] < 0) & (panel["prev_gap"] < 0))
    panel["growth_signal"] = ((panel["year"] - panel["prev_year"] == 1)
                              & (panel["desire_gap"] > 0) & (panel["prev_gap"] > 0))
    for col in ["usage", "desire", "admiration", "year"]:
        panel[f"next_{col}"] = group[col].shift(-1)
    panel["has_next"] = panel["next_year"] - panel["year"] == 1
    for col in ["usage", "desire", "admiration"]:
        panel[f"delta_{col}"] = panel[f"next_{col}"] - panel[col]
    return panel


def confusion_stats(df, outcome):
    use = df.dropna(subset=[outcome]).copy()
    truth = use[outcome] < 0
    pred = use["warning"]
    return {"样本": len(use), "警报数": int(pred.sum()), "实际下降数": int(truth.sum()),
            "警报后下降": int((pred & truth).sum()),
            "精确率": precision_score(truth, pred, zero_division=0),
            "召回率": recall_score(truth, pred, zero_division=0),
            "平衡准确率": balanced_accuracy_score(truth, pred) if truth.nunique() == 2 else np.nan,
            "无警报下降率": float(truth[~pred].mean()) if (~pred).any() else np.nan}


def clustered_risk_difference(df, outcome, draws=2000):
    """按技术重采样，给出警报组与非警报组下降率之差的描述性区间。"""
    data = df.dropna(subset=[outcome]).copy()
    data["key"] = data["category"].astype(str) + "/" + data["tech"].astype(str)
    groups = [g for _, g in data.groupby("key")]
    rng = np.random.default_rng(42)
    vals = []
    for _ in range(draws):
        sample = pd.concat([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        a = sample[sample.warning][outcome].lt(0)
        b = sample[~sample.warning][outcome].lt(0)
        if len(a) and len(b):
            vals.append(float(a.mean() - b.mean()))
    observed = (data.loc[data.warning, outcome].lt(0).mean()
                - data.loc[~data.warning, outcome].lt(0).mean())
    return observed, *np.quantile(vals, [0.025, 0.975])


def main():
    panel = pd.read_csv(DATA / "panel.csv", encoding="utf-8-sig")
    panel = add_warning(panel)
    # 仅纳入当年有前一年、下一年真实观测的技术。
    val = panel[panel["has_next"] & panel["prev_year"].notna()
                & ((panel["year"] - panel["prev_year"]) == 1)].copy()
    rows = []
    for target in ["usage", "desire", "admiration"]:
        d = val.dropna(subset=[target, f"delta_{target}"])
        diff, lo, hi = clustered_risk_difference(d, f"delta_{target}")
        rows.append({"因变量": f"下一年{target}下降", **confusion_stats(d, f"delta_{target}"),
                     "风险差": diff, "区间下限": lo, "区间上限": hi})
    pd.DataFrame(rows).to_csv(OUT / "warning_validation_so.csv", index=False, encoding="utf-8-sig")
    val[["tech", "category", "year", "usage", "desire_gap", "admiration", "warning",
         "growth_signal", "delta_usage", "delta_desire", "delta_admiration"]].to_csv(
             OUT / "warning_validation_cases.csv", index=False, encoding="utf-8-sig")
    print("调查面板前瞻验证：")
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    yearly = val.groupby("year").apply(
        lambda g: pd.Series({"样本": len(g), "警报": int(g.warning.sum()),
                             "警报后usage下降率": g.loc[g.warning, "delta_usage"].lt(0).mean(),
                             "无警报usage下降率": g.loc[~g.warning, "delta_usage"].lt(0).mean()}),
        include_groups=False).reset_index()
    yearly.to_csv(OUT / "warning_validation_by_year.csv", index=False, encoding="utf-8-sig")
    print("\n按预警年份：")
    print(yearly.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    gh_file = DATA / "github_comment_yearly.csv"
    if not gh_file.exists():
        print("未发现 GitHub 评论数据，跳过跨平台检验。")
        return
    gh = pd.read_csv(gh_file, encoding="utf-8-sig")
    gh = gh.sort_values(["tech", "year"])
    gh["prev_count"] = gh.groupby("tech")["issue_pr_comments"].shift(1)
    gh["prev_year"] = gh.groupby("tech")["year"].shift(1)
    gh["comment_momentum"] = np.where(
        gh["year"] - gh["prev_year"] == 1,
        np.log1p(gh["issue_pr_comments"]) - np.log1p(gh["prev_count"]), np.nan)
    gh["next_count"] = gh.groupby("tech")["issue_pr_comments"].shift(-1)
    gh["next_year"] = gh.groupby("tech")["year"].shift(-1)
    gh["delta_comment_log"] = np.log1p(gh["next_count"]) - np.log1p(gh["issue_pr_comments"])
    # GitHub 评论量下一年变化是独立结果变量，不把未来评论用于当年预警。
    joined = panel.merge(gh[["tech", "repo", "year", "issue_pr_comments", "next_count",
                             "next_year", "delta_comment_log", "comment_momentum"]],
                         on=["tech", "year"], how="inner", suffixes=("_so", "_gh"))
    joined = joined[(joined["next_year_gh"] - joined["year"] == 1)
                    & joined["prev_year"].notna()
                    & ((joined["year"] - joined["prev_year"]) == 1)].copy()
    joined["comment_down"] = joined["next_count"] < joined["issue_pr_comments"]
    joined["discordant"] = joined["warning"] != joined["comment_down"]
    joined.to_csv(OUT / "warning_validation_github_cases.csv", index=False, encoding="utf-8-sig")
    gh_stats = confusion_stats(joined, "delta_comment_log")
    pd.DataFrame([{"因变量": "下一年主仓对话评论量下降", **gh_stats}]).to_csv(
        OUT / "warning_validation_github.csv", index=False, encoding="utf-8-sig")
    print("\nGitHub 独立因变量：")
    print(pd.DataFrame([gh_stats]).to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\n逐项跨平台对照：")
    print(joined[["tech", "year", "warning", "issue_pr_comments", "next_count",
                  "comment_down", "discordant"]].to_string(index=False))

    # 当年可用的两个平台信号：问卷预警 + 截至当年的评论动量。
    latest = panel.merge(gh[["tech", "repo", "year", "issue_pr_comments",
                             "comment_momentum"]], on=["tech", "year"], how="inner")
    latest = latest[latest["year"] == latest["year"].max()].copy()
    latest["so_history_ok"] = latest["year"] - latest["prev_year"] == 1
    latest["信号组合"] = np.select(
        [~latest.so_history_ok,
         latest.warning & (latest.comment_momentum < 0),
         latest.warning & (latest.comment_momentum >= 0),
         ~latest.warning & (latest.comment_momentum < 0)],
        ["问卷历史不足", "双源收缩", "问卷警报但评论未降", "评论收缩但问卷未警报"],
        default="未触发收缩信号")
    latest[["tech", "repo", "year", "usage", "desire_gap", "admiration",
            "issue_pr_comments", "comment_momentum", "warning", "so_history_ok", "信号组合"]].to_csv(
                OUT / "multisignal_warning_latest.csv", index=False, encoding="utf-8-sig")
    print("\n当年双源信号（仅用于优先核查，不当作已校准概率）：")
    print(latest[["tech", "year", "warning", "comment_momentum", "信号组合"]].to_string(index=False))


if __name__ == "__main__":
    main()
