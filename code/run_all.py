# -*- coding: utf-8 -*-
"""
一键运行：依次执行「不足与后续工作」的全部内容。

用法：
    python run_all.py

特性：
    1. 运行前自动检查可选依赖（shap / xgboost / lightgbm / networkx），
       缺失时尝试用当前 Python 自动安装（python -m pip install ...）。
    2. 若某个脚本因缺依赖退出（退出码 2），会跳过该步并继续运行其余步骤，
       而不是整体崩溃；最后打印各步骤执行情况汇总。

流程：
    02 构建面板 -> 03 真实数据回归验证 -> 04 SHAP 归因
    -> 05 图特征 -> 06 三模型对比 -> 07 早期预警基线
    -> 09 原规则回测 -> 10 双源动态预警回测
（01 数据下载默认自动判断，仅当 data/raw/ 缺文件时才联网下载）
"""
import os
import subprocess
import sys

import config
from utils import missing_optional_deps

# 需要执行的所有步骤（按顺序）
STEPS = [
    "02_build_panel.py",
    "03_regression_validation.py",
    "04_shap_analysis.py",
    "05_graph_features.py",
    "06_boosting_models.py",
    "07_early_warning_system.py",
    "09_validate_multisignal_warning.py",
    "10_compare_multisignal_warning.py",
]


def ensure_optional_deps():
    """检查并（可选）自动安装缺失的可选依赖。返回是否全部就绪。"""
    missing = missing_optional_deps()
    if not missing:
        return True

    print("=" * 72)
    print("[依赖检查] 检测到以下可选依赖缺失：")
    for imp, pip_name in missing:
        print(f"    - {imp}  (pip install {pip_name})")
    print("正在尝试用当前 Python 自动安装 ...")
    print("=" * 72)

    pkgs = [pip_name for _, pip_name in missing]
    code = subprocess.call(
        [sys.executable, "-m", "pip", "install", *pkgs])

    still_missing = missing_optional_deps()
    if not still_missing:
        print("[依赖检查] 安装完成，全部依赖就绪。\n")
        return True
    print("[依赖检查] 自动安装未完全成功，剩余缺失：")
    for imp, pip_name in still_missing:
        print(f"    - {imp}  ->  请手动执行: pip install {pip_name}")
    print("（涉及这些依赖的步骤将被跳过，其余步骤正常执行）\n")
    return False


def run(script: str) -> int:
    print("\n" + "#" * 72)
    print(f"# 运行 {script}")
    print("#" * 72)
    path = os.path.join(config.BASE_DIR, script)
    return subprocess.call([sys.executable, path], cwd=config.BASE_DIR)


def main():
    deps_ready = ensure_optional_deps()

    # 0. 数据下载（缺文件才触发）
    if not all(os.path.exists(os.path.join(config.RAW_DIR, f"so_survey_{y}.zip"))
               for y in config.YEARS):
        print("[数据] 检测到 data/raw/ 缺少文件，先下载 ...")
        subprocess.call([sys.executable,
                         os.path.join(config.BASE_DIR, "01_download_data.py")],
                        cwd=config.BASE_DIR)

    # 1. 依次执行各步骤
    results = []  # (script, status)
    for script in STEPS:
        code = run(script)
        if code == 0:
            results.append((script, "成功"))
        elif code == 2:
            results.append((script, "跳过（缺依赖）"))
        else:
            results.append((script, f"失败（退出码 {code}）"))

    # 2. 汇总
    print("\n" + "=" * 72)
    print("执行情况汇总：")
    for script, status in results:
        print(f"    {script:<32} {status}")
    print("=" * 72)
    ok = all(s == "成功" or s == "跳过（缺依赖）" for _, s in results)
    if ok:
        print("流程结束。结果与图表见 results/ 目录；")
        print("若存在「跳过」步骤，补齐对应依赖后重跑即可。")
    else:
        print("存在失败步骤，请检查上方报错。")
    print("=" * 72)


if __name__ == "__main__":
    main()
