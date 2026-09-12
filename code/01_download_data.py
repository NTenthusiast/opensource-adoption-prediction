# -*- coding: utf-8 -*-
"""
步骤一：下载 Stack Overflow 官方开发者调查数据（2018–2022）。

用法：
    python 01_download_data.py

说明：
    - 默认下载 config.DOWNLOAD_URLS 中登记的五年数据到 data/raw/。
    - 若网络受限或链接失效，可手动到 Stack Overflow 官网下载对应的
      "Developer Survey Results" zip，放入 data/raw/ 并命名为
      so_survey_{年份}.zip 即可，本脚本会自动跳过已存在的文件。
"""
import os
import sys
import zipfile

import config
from config import DOWNLOAD_URLS, RAW_DIR


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
    print("全部下载/校验完成。")


if __name__ == "__main__":
    main()
