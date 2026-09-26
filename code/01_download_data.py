# -*- coding: utf-8 -*-
"""
步骤一：下载 Stack Overflow 官方开发者调查数据（2018–2025）。

用法：
    python 01_download_data.py

说明：
    - 旧版 ZIP 与新版官方 GitHub CSV 均下载到 data/raw/。
    - 若网络受限或链接失效，可手动到 Stack Overflow 官网下载对应的
      "Developer Survey Results" zip，放入 data/raw/ 并命名为
      so_survey_{年份}.zip 即可，本脚本会自动跳过已存在的文件。
"""
import os
import sys
import zipfile

import config
from config import DOWNLOAD_URLS, RAW_DIR

RECENT_REF = "32a114542da67e3759479637343718502742adfd"
RECENT_SIZES = {2023: 158626799, 2024: 159525875, 2025: 140893245}
RECENT_URLS = {
    y: f"https://media.githubusercontent.com/media/StackExchange/Survey/{RECENT_REF}/packages/archive/{y}/results.csv"
    for y in (2023, 2024, 2025)
}


def download_one(year: int, url: str) -> str:
    target = os.path.join(RAW_DIR, f"so_survey_{year}.zip")
    if os.path.exists(target) and zipfile.is_zipfile(target):
        print(f"[跳过] {year} 已存在: {target}")
        return target
    print(f"[下载] {year} <- {url}")
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600) as r, open(target, "wb") as f:
        while True:
            chunk = r.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)
    print(f"[完成] {year} -> {target} ({os.path.getsize(target)/1e6:.1f} MB)")
    return target


def main():
    for year, url in DOWNLOAD_URLS.items():
        download_one(year, url)
    import urllib.request
    for year, url in RECENT_URLS.items():
        target = os.path.join(RAW_DIR, f"so_survey_{year}.csv")
        if os.path.exists(target) and os.path.getsize(target) == RECENT_SIZES[year]:
            print(f"[跳过] {year} 已存在: {target}")
            continue
        partial = target + ".part"
        print(f"[下载] {year} <- {url}")
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=600) as source, open(partial, "wb") as dest:
            while chunk := source.read(1024 * 1024):
                dest.write(chunk)
        with open(partial, "rb") as check:
            if b"ResponseId" not in check.readline():
                raise ValueError(f"{year} 年官方 CSV 表头无效：{partial}")
        if os.path.getsize(partial) != RECENT_SIZES[year]:
            raise ValueError(f"{year} 年官方 CSV 大小不符：{partial}")
        os.replace(partial, target)
        print(f"[完成] {year} -> {target} ({os.path.getsize(target)/1e6:.1f} MB)")
    print("全部下载或按文件大小复核完成。")


if __name__ == "__main__":
    main()
