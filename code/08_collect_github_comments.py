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
    "Ruby": "ruby/ruby",
    "Kotlin": "JetBrains/kotlin",
    "Elixir": "elixir-lang/elixir",
    "Erlang": "erlang/otp",
    "Julia": "JuliaLang/julia",
    "PowerShell": "PowerShell/PowerShell",
    "PHP": "php/php-src",
    "Scala": "scala/scala",
    "Crystal": "crystal-lang/crystal",
    "Swift": "swiftlang/swift",
    "Go": "golang/go",
    "Dart": "dart-lang/sdk",
    "Rust": "rust-lang/rust",
    "TypeScript": "microsoft/TypeScript",
    "Python": "python/cpython",
    "Java": "openjdk/jdk",
    "FastAPI": "fastapi/fastapi",
    "Svelte": "sveltejs/svelte",
    "Vue": "vuejs/core",
    "Nuxt.js": "nuxt/nuxt",
    "Laravel": "laravel/framework",
    "Symfony": "symfony/symfony",
    "Deno": "denoland/deno",
    "Gatsby": "gatsbyjs/gatsby",
    "Next.js": "vercel/next.js",
    "React.js": "facebook/react",
    "Angular": "angular/angular",
    "Node.js": "nodejs/node",
    "Redis": "redis/redis",
    "Neo4j": "neo4j/neo4j",
    "C#": "dotnet/csharplang",
    "F#": "dotnet/fsharp",
    "OCaml": "ocaml/ocaml",
    "H2": "h2database/h2database",
    "DuckDB": "duckdb/duckdb",
    "Clickhouse": "ClickHouse/ClickHouse",
    "InfluxDB": "influxdata/influxdb",
    "Supabase": "supabase/supabase",
    "NestJS": "nestjs/nest",
    "Spring Boot": "spring-projects/spring-boot",
    "Zig": "ziglang/zig",
    "Django": "django/django",
    "Cassandra": "apache/cassandra",
}
YEARS = range(2021, 2026)
PER_PAGE = 100
# GitHub 的 since 筛选“最后更新时间”，因此所有在 2021 年及以后创建的
# 评论都会被保留；更早创建但后来编辑的评论仍会按 created_at 排除。
SINCE = "2020-12-31T00:00:00Z"


def api(repo, page, headers=False):
    path = (f"repos/{repo}/issues/comments?per_page={PER_PAGE}"
            f"&sort=created&direction=asc&since={SINCE}&page={page}")
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
    if n_pages == 0:
        return [(y, 0) for y in YEARS], 0, 0
    cache = {}

    def page_data(page):
        if page not in cache:
            cache[page] = json.loads(api(repo, page))
        return cache[page]

    if n_pages >= 300 and page_data(n_pages)[-1]["created_at"] < "2026-01-01":
        raise RuntimeError(f"{repo} 的分页未覆盖完整研究窗口，不能保证计数")

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

    starts = {y: lower_bound(f"{y}-01-01T00:00:00Z") for y in list(YEARS) + [2026]}
    return [(y, starts[y + 1] - starts[y]) for y in YEARS], n_pages, len(cache)


def main():
    global YEARS, SINCE
    args = sys.argv[1:]
    if "--start-year" in args:
        ix = args.index("--start-year")
        start_year = int(args[ix + 1])
        del args[ix:ix + 2]
        if start_year < 2021 or start_year > 2023:
            raise ValueError("起始年份只支持 2021—2023")
        YEARS = range(start_year, 2026)
        SINCE = f"{start_year - 1}-12-31T00:00:00Z"
    if "--probe" in args:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def probe(item):
            tech, repo = item
            try:
                pages = last_page(repo)
                vals = json.loads(api(repo, pages)) if pages else []
                end = vals[-1]["created_at"] if vals else "空"
                return tech, repo, pages, end, (pages < 300 or end >= "2026-01-01")
            except RuntimeError as exc:
                return tech, repo, 0, str(exc), False

        names = [v for v in args if v != "--probe"]
        if names and (set(names) - set(REPOS)):
            raise ValueError(f"未知技术：{set(names) - set(REPOS)}")
        items = [(tech, repo) for tech, repo in REPOS.items() if not names or tech in names]
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(probe, item) for item in items]
            for future in as_completed(futures):
                print(*future.result(), flush=True)
        return
    selected = args
    unknown = sorted(set(selected) - set(REPOS))
    if unknown:
        raise ValueError(f"未知技术：{unknown}；可选：{list(REPOS)}")
    chosen = {k: v for k, v in REPOS.items() if not selected or k in selected}
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def collect(item):
        tech, repo = item
        counts, pages, calls = yearly_counts(repo)
        return tech, repo, counts, pages, calls

    rows = []
    errors = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(collect, item) for item in chosen.items()]
        for future in as_completed(futures):
            try:
                tech, repo, counts, pages, calls = future.result()
            except Exception as exc:
                errors.append(str(exc))
                print(f"跳过：{exc}", flush=True)
                continue
            print(f"{tech}: 仓库={repo}, 总页数={pages}, 已读取页数={calls}", flush=True)
            for year, count in counts:
                print(f"  {year}: {count}", flush=True)
                rows.append({"tech": tech, "repo": repo, "year": year,
                             "issue_pr_comments": count,
                             "collected_utc": datetime.now(timezone.utc).isoformat()})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError("没有仓库采集成功，原有年度计数保持不变")
    fresh = pd.DataFrame(rows)
    if OUT.exists():
        previous = pd.read_csv(OUT, encoding="utf-8-sig")
        fresh = pd.concat([previous[~previous.tech.isin(fresh.tech.unique())], fresh], ignore_index=True)
        fresh = fresh.drop_duplicates(["tech", "year"], keep="last")
    fresh.sort_values(["tech", "year"]).to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"已保存 {OUT}")
    if errors:
        print(f"共有 {len(errors)} 个仓库未采集成功；对应技术不纳入完整年度回测。")


if __name__ == "__main__":
    main()
