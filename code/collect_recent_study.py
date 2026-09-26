"""复现近期回测使用的 27 个主仓年度评论计数。"""
import subprocess
import sys
from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parent
COLLECTOR = BASE / "08_collect_github_comments.py"
GROUP_2021 = [
    "jQuery", "Express", "Flask", "Fastify", "Phoenix", "Ruby", "Kotlin",
    "Elixir", "Erlang", "Scala", "Crystal", "Vue", "FastAPI", "Gatsby",
    "Redis", "Neo4j", "C#", "F#", "OCaml", "H2", "InfluxDB", "NestJS",
]
GROUP_2023 = ["Svelte", "Laravel", "Deno", "DuckDB", "Spring Boot"]


def main():
    for start_year, names in [(2021, GROUP_2021), (2023, GROUP_2023)]:
        cmd = [sys.executable, str(COLLECTOR), "--start-year", str(start_year), *names]
        subprocess.run(cmd, check=True)
    data = pd.read_csv(BASE / "data" / "processed" / "github_comment_yearly.csv",
                       encoding="utf-8-sig")
    for start_year, names in [(2021, GROUP_2021), (2023, GROUP_2023)]:
        required = set(range(start_year, 2026))
        for name in names:
            observed = set(data.loc[data.tech == name, "year"])
            if not required.issubset(observed):
                raise ValueError(f"{name} 缺少年份 {sorted(required - observed)}")
    print("近期回测所需的 27 个仓库年度计数已齐全。")


if __name__ == "__main__":
    main()
