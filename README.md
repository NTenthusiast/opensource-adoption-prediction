# 开源技术采纳率预测与竞争力归因研究

> **研究更新**：新实验将七个公开主仓的 GitHub 对话评论量纳入数据，在五项有连续问卷历史的技术上回测“问卷信号＋评论信号”的预警规则。请先阅读 [研究记录_多源因变量与动态预警.md](研究记录_多源因变量与动态预警.md)；下文是早期阶段的历史说明。旧报告把跨年回归系数解释为个人留存/转化率、把负渴望缺口直接解释为净流出，均超出数据能支持的范围。

> 指导教师：汪亮（南京大学）　·　本科生科研训练项目

本项目以 **Stack Overflow 2018–2022 开发者调查数据** 为研究对象，构建“技术 × 年份”表格面板，
对比多种机器学习模型的采纳率预测能力，并引入 SHAP 归因与网络图特征，对开源技术的竞争力来源进行归因分析。

研究产出了 **组会汇报 PPT** 与 **论文初稿**（LaTeX）。

## 目录结构

```
├── paper/                 # 论文初稿（LaTeX）
│   ├── main.tex           # 论文正文
│   └── cjc.cls            # 期刊模板
├── code/                  # 实验代码（五项后续工作）
│   ├── README.md          # 代码库详细说明与核心结果
│   ├── config.py          # 全局配置（路径 / 年份 / 列名映射）
│   ├── 01_download_data.py          # 下载官方调查数据
│   ├── 02_build_panel.py            # 构建「技术×年份」面板 + 滞后特征
│   ├── 03_regression_validation.py  # 真实数据验证 β1 / β2
│   ├── 04_shap_analysis.py          # SHAP 归因
│   ├── 05_graph_features.py         # 网络图特征（PageRank / 度 / 社区）
│   ├── 06_boosting_models.py        # RF / XGBoost / LightGBM 对比
│   ├── 07_early_warning_system.py   # 三维动态预警系统
│   ├── run_all.py         # 一键运行
│   ├── make_ppt.py        # 生成组会汇报 PPT
│   └── data/ results/     # 处理后的数据与结果图表
└── .gitignore
```

## 核心结论

| 任务 | 方法与结果 |
|---|---|
| 采纳率预测 | 随机森林 / XGBoost / LightGBM 时间切分对比，测试集 R² 由 **0.9656** 提升至 **0.9719** |
| 竞争力归因 | SHAP 归因 + 网络 PageRank / 加权度 / 社区图特征，定位技术竞争力的主要来源 |
| 衰退预警 | “存量–增量–口碑”三维动态预警，159 项技术中识别 52 项衰退、34 项增长 |

## 复现方法

```bash
cd code
pip install -r requirements.txt
python run_all.py        # 一键运行全部流程（数据缺失时自动下载）
python make_ppt.py       # 生成组会汇报 PPT
```

> 原始调查数据（约 68 MB）已加入 `.gitignore`，脚本 `01_download_data.py` 会自动从
> Stack Overflow 官方地址下载；处理后的面板数据（`code/data/processed/`）已入库，可直接复现回归与建模结果。

更详细的结果说明与「不足与后续工作」的对应关系见 [`code/README.md`](code/README.md)。
