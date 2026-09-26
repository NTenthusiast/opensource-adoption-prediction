"""采集公开仓库逐年 Issue/PR 对话评论数量（不保存评论正文或用户身份）。

通过 GitHub REST API 按创建时间排序，二分定位每年起点。统计的是
Issue 与 PR 的对话评论，不含 PR 行内 review 评论；机器人也计入。
每项技术仅映射一个主仓，结果不能代表整项技术的全部社区活动。
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
OUT = BASE / "data" / "processed" / "github_comment_yearly.csv"
REPOS = {
    "jQuery": "jquery/jquery",
    "Express": "expressjs/express",
    "Flask": "pallets/flask",
    "Fastify": "fastify/fastify",
    "Phoenix": "phoenixframework/phoenix",
}
YEARS = range(2018, 2024)
PER_PAGE = 100


def api(repo, page, headers=False):
    path = (f"repos/{repo}/issues/comments?per_page={PER_PAGE}"
            f"&sort=created&direction=asc&page={page}")
    cmd = ["gh", "api", "-X", "GET"] + (["-i"] if headers else []) + [path]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if p.returncode:
        raise RuntimeError(f"GitHub API 失败：{repo} 第{page}页：{p.stderr.strip()}")
    return p.stdout


def last_page(repo):
    raw = api(repo, 1, headers=True)
    head, body = raw.split("\n\n", 1)
    match = re.search(r"<[^>]*[?&]page=(\d+)>; rel=\"last\"", head)
    if not match:
        return 1 if json.loads(body) else 0
    return int(match.group(1))


def yearly_counts(repo):
    n_pages = last_page(repo)
    cache = {}

    def page_data(page):
        if page not in cache:
            cache[page] = json.loads(api(repo, page))
        return cache[page]

    if n_pages >= 300:
        raise RuntimeError(f"{repo} 达到 API 300 页上限，不能保证完整计数")
    if page_data(n_pages)[-1]["created_at"] < "2024-01-01":
        raise RuntimeError(f"{repo} 的分页未覆盖完整研究窗口")

    def lower_bound(dt):
        lo, hi = 1, n_pages
        while lo < hi:
            mid = (lo + hi) // 2
            vals = page_data(mid)
            if not vals or vals[-1]["created_at"] >= dt:
                hi = mid
            else:
                lo = mid + 1
        vals = page_data(lo)
        ix = next((i for i, x in enumerate(vals) if x["created_at"] >= dt), len(vals))
        return (lo - 1) * PER_PAGE + ix

    starts = {y: lower_bound(f"{y}-01-01T00:00:00Z") for y in list(YEARS) + [2024]}
    return [(y, starts[y + 1] - starts[y]) for y in YEARS], n_pages, len(cache)


def main():
    if "--probe" in sys.argv:
        candidates = ["jquery/jquery", "fastify/fastify", "phoenixframework/phoenix",
                      "elixir-lang/elixir", "scala/scala", "neo4j/neo4j"]
        for repo in candidates:
            pages = last_page(repo)
            vals = json.loads(api(repo, pages))
            print(repo, pages, vals[0]["created_at"] if vals else "空",
                  vals[-1]["created_at"] if vals else "空", flush=True)
        return
    rows = []
    for tech, repo in REPOS.items():
        counts, pages, calls = yearly_counts(repo)
        print(f"{tech}: 仓库={repo}, 总页数={pages}, 已读取页数={calls}", flush=True)
        for year, count in counts:
            print(f"  {year}: {count}", flush=True)
            rows.append({"tech": tech, "repo": repo, "year": year,
                         "issue_pr_comments": count,
                         "collected_utc": datetime.now(timezone.utc).isoformat()})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"已保存 {OUT}")


if __name__ == "__main__":
    main()
