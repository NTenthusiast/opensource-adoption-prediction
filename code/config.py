# -*- coding: utf-8 -*-
"""
全局配置：路径、年份、列名映射、技术领域映射、随机种子等。

本文件是「开源技术采纳率预测与竞争力归因研究——不足与后续工作」代码库的
统一配置入口，其余脚本均从这里读取配置，保证口径一致。
"""
import os

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
FIG_DIR = os.path.join(RESULTS_DIR, "figures")
TABLE_DIR = os.path.join(RESULTS_DIR, "tables")

for _d in (RAW_DIR, PROCESSED_DIR, FIG_DIR, TABLE_DIR):
    os.makedirs(_d, exist_ok=True)

# ---------------------------------------------------------------------------
# 真实数据下载地址（Stack Overflow 官方托管，2018–2022 已稳定多年）
# 2016/2017 数据托管于 Dropbox 且题目格式差异较大；2023/2024 需通过网页表单
# 下载（JS 渲染）。为保持口径一致，本代码默认使用 2018–2022 五年窗口。
# 如需扩展年份，只需在下面字典中补充 {年份: 下载地址} 即可。
# ---------------------------------------------------------------------------
DOWNLOAD_URLS = {
    2018: "https://info.stackoverflowsolutions.com/rs/719-EMH-566/images/stack-overflow-developer-survey-2018.zip",
    2019: "https://info.stackoverflowsolutions.com/rs/719-EMH-566/images/stack-overflow-developer-survey-2019.zip",
    2020: "https://info.stackoverflowsolutions.com/rs/719-EMH-566/images/stack-overflow-developer-survey-2020.zip",
    2021: "https://info.stackoverflowsolutions.com/rs/719-EMH-566/images/stack-overflow-developer-survey-2021.zip",
    2022: "https://info.stackoverflowsolutions.com/rs/719-EMH-566/images/stack-overflow-developer-survey-2022.zip",
}

YEARS = sorted(DOWNLOAD_URLS.keys())  # [2018, 2019, 2020, 2021, 2022]

# ---------------------------------------------------------------------------
# 领域（Category）与列名映射
# 说明：2020 及以前用 "{Category}WorkedWith / {Category}DesireNextYear"，
#       2021 及以后改用 "{Category}HaveWorkedWith / {Category}WantToWorkWith"。
# 这里仅选取五年全部一致出现的四大领域（语言/数据库/平台/Web框架），
# 与原始论文的五领域口径对应，但去掉了仅在部分年份出现的 MiscTech/ToolsTech
# 等不稳定类别，以保证跨年可比。
# ---------------------------------------------------------------------------
# 每个领域：{年段: (使用列, 渴望列)}
CATEGORY_COLUMNS = {
    "Language": {
        (2018, 2020): ("LanguageWorkedWith", "LanguageDesireNextYear"),
        (2021, 2022): ("LanguageHaveWorkedWith", "LanguageWantToWorkWith"),
    },
    "Database": {
        (2018, 2020): ("DatabaseWorkedWith", "DatabaseDesireNextYear"),
        (2021, 2022): ("DatabaseHaveWorkedWith", "DatabaseWantToWorkWith"),
    },
    "Platform": {
        (2018, 2020): ("PlatformWorkedWith", "PlatformDesireNextYear"),
        (2021, 2022): ("PlatformHaveWorkedWith", "PlatformWantToWorkWith"),
    },
    "Webframework": {
        (2018, 2018): ("FrameworkWorkedWith", "FrameworkDesireNextYear"),
        (2019, 2019): ("WebFrameWorkedWith", "WebFrameDesireNextYear"),
        (2020, 2020): ("WebframeWorkedWith", "WebframeDesireNextYear"),
        (2021, 2022): ("WebframeHaveWorkedWith", "WebframeWantToWorkWith"),
    },
}

CATEGORY_CN = {
    "Language": "编程语言",
    "Database": "数据库",
    "Platform": "平台工具",
    "Webframework": "Web框架",
}

# 原始论文（169 项技术、五领域）用于对照的模拟参数
SIM_BETA1 = 0.80   # 模拟数据内置的「采纳惯性」
SIM_BETA2 = 0.23   # 模拟数据内置的「渴望转化率」

# 随机种子与模型设定
RANDOM_STATE = 42
TEST_YEAR = 2022          # 时序切分：测试集年份（最后一年）
LAG_ORDER = 3             # 随机森林最多使用的滞后阶数

# 预警系统阈值：渴望缺口连续为负的年份数
WARNING_CONSECUTIVE_YEARS = 2


def resolve_columns(category: str, year: int):
    """返回某领域在某年的 (使用列, 渴望列)。"""
    for (lo, hi), cols in CATEGORY_COLUMNS[category].items():
        if lo <= year <= hi:
            return cols
    raise KeyError(f"未找到 {category} 在 {year} 年的列名映射")
