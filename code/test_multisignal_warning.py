"""检查预警只使用当年及以前信息，并拒绝断裂的年份序列。"""
import importlib

import pandas as pd

prepare = importlib.import_module("10_compare_multisignal_warning").prepare


def fixture():
    so = pd.DataFrame([
        {"tech": "示例", "category": "Language", "year": year,
         "usage": 0.4, "desire": 0.3, "desire_gap": -0.1, "admiration": 0.5}
        for year in [2018, 2019, 2020, 2021]
    ])
    gh = pd.DataFrame([
        {"tech": "示例", "repo": "example/repo", "year": year,
         "issue_pr_comments": count}
        for year, count in [(2018, 100), (2019, 90), (2020, 80), (2021, 70), (2022, 60)]
    ])
    return so, gh


def main():
    so, gh = fixture()
    base = prepare(so, gh).set_index("year")
    assert bool(base.loc[2020, "double_alert"])
    assert bool(base.loc[2020, "eligible"])
    assert bool(base.loc[2020, "future_gh_ok"])

    # 改变未来一年评论量，只能改变结果标签，不能反向改变当年的警报。
    changed = gh.copy()
    changed.loc[changed.year == 2021, "issue_pr_comments"] = 9000
    retest = prepare(so, changed).set_index("year")
    assert bool(retest.loc[2020, "double_alert"])
    assert bool(retest.loc[2020, "comments_down"]) != bool(base.loc[2020, "comments_down"])

    # 缺失上一年问卷时不能假装拥有连续两年历史。
    missing = prepare(so[so.year != 2019], gh).set_index("year")
    assert not bool(missing.loc[2020, "eligible"])
    assert missing.loc[2020, "状态"] == "问卷历史不足"
    print("双源预警时间边界测试通过")


if __name__ == "__main__":
    main()
