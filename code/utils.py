# -*- coding: utf-8 -*-
"""
共享工具函数：多选字段解析、技术名规范化、评价指标、绘图风格等。
"""
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # 无显示环境也能出图
import matplotlib.pyplot as plt
from config import CATEGORY_CN, RANDOM_STATE

# 中文字体（Windows 使用 SimHei / Microsoft YaHei）
for _f in ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC"]:
    try:
        plt.rcParams["font.sans-serif"] = [_f]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False


# ---------------------------------------------------------------------------
# 多选字段解析
# ---------------------------------------------------------------------------
def parse_multiselect(series: pd.Series) -> list:
    """把 'JavaScript;Python;NA' 形式的多选列解析为每个受访者的技术集合。

    返回 list[set[str]]，NA/缺失 -> 空集合。
    """
    out = []
    for v in series:
        if pd.isna(v):
            out.append(set())
            continue
        s = str(v).strip()
        if s in ("", "NA", "nan", "None"):
            out.append(set())
            continue
        out.append({t.strip() for t in s.split(";") if t.strip()})
    return out


# ---------------------------------------------------------------------------
# 技术名规范化
# ---------------------------------------------------------------------------
_ALIASES = {
    ".NET Core": ".NET",
    ".NET 5": ".NET",
    ".NET 6": ".NET",
    "Node.js": "Node.js",
    "NodeJS": "Node.js",
    "Angular.js": "Angular",
    "AngularJS": "Angular",
    "jQuery": "jQuery",
    "Vue.js": "Vue",
    "Deno": "Deno",
}


def normalize_tech_name(name: str) -> str:
    """去除首尾空白并统一已知别名，提升跨年匹配率。"""
    name = str(name).strip()
    return _ALIASES.get(name, name)


def split_pairs(names: list) -> list:
    """把 "HTML/CSS"、"Bash/Shell" 这类复合选项拆成若干子技术，便于跨年对齐。"""
    out = []
    for n in names:
        out.extend([x.strip() for x in re.split(r"[/,]", n) if x.strip()])
    return out


# ---------------------------------------------------------------------------
# 评价指标
# ---------------------------------------------------------------------------
def metrics(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    return {"R2": r2, "RMSE": rmse, "MAE": mae}


def fmt_metrics(m: dict) -> str:
    return f"R²={m['R2']:.4f}  RMSE={m['RMSE']:.4f}  MAE={m['MAE']:.4f}"


# ---------------------------------------------------------------------------
# 可选依赖检查（避免缺失时直接崩溃，给出清晰提示）
# ---------------------------------------------------------------------------
# 需要哪些可选依赖：{import 名: pip 包名}
OPTIONAL_DEPS = {
    "shap": "shap",
    "xgboost": "xgboost",
    "lightgbm": "lightgbm",
    "networkx": "networkx",
}


def ensure_optional(import_name: str, pip_name: str = None):
    """导入可选依赖；若缺失，打印清晰安装提示并返回 None（调用方自行跳过/退出）。"""
    pip_name = pip_name or OPTIONAL_DEPS.get(import_name, import_name)
    try:
        return __import__(import_name)
    except ImportError:
        print(f"\n[依赖缺失] 未找到模块 '{import_name}'。")
        print(f"           请先安装：pip install {pip_name}\n")
        return None


def missing_optional_deps():
    """返回当前环境中缺失的可选依赖列表（[(import名, pip名), ...]）。"""
    import importlib.util
    missing = []
    for imp, pip_name in OPTIONAL_DEPS.items():
        if importlib.util.find_spec(imp) is None:
            missing.append((imp, pip_name))
    return missing


# ---------------------------------------------------------------------------
# 统一绘图样式
# ---------------------------------------------------------------------------
PALETTE = {
    "blue": "#2c6fbb",
    "red": "#c0392b",
    "green": "#27ae60",
    "orange": "#e67e22",
    "purple": "#8e44ad",
    "grey": "#7f8c8d",
}


def save_fig(fig, name: str):
    """保存图片并返回路径。"""
    import config
    path = f"{config.FIG_DIR}/{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path
