# -*- coding: utf-8 -*-
"""
生成组会汇报 PPT：《开源技术采纳率预测与竞争力归因研究——不足与后续工作进展》。

运行：python make_ppt.py
输出：组会汇报_不足与后续工作进展.pptx（16:9，约 11 页，30 分钟可讲完）

依赖：python-pptx（pip install python-pptx）
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

import config

# ---------------------------------------------------------------------------
# 主题
# ---------------------------------------------------------------------------
BLUE = RGBColor(0x2C, 0x6F, 0xBB)
DARK = RGBColor(0x1F, 0x29, 0x37)
GREY = RGBColor(0x6B, 0x72, 0x80)
LIGHT = RGBColor(0xF3, 0xF6, 0xFA)
ORANGE = RGBColor(0xE6, 0x7E, 0x22)
GREEN = RGBColor(0x27, 0xAE, 0x60)
RED = RGBColor(0xC0, 0x39, 0x2B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

FONT = "Microsoft YaHei"
FIG_DIR = config.FIG_DIR

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def add_slide():
    return prs.slides.add_slide(BLANK)


def add_rect(slide, x, y, w, h, fill, line=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1)
    shp.shadow.inherit = False
    return shp


def add_text(slide, x, y, w, h, text, size=18, color=DARK, bold=False,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line_spacing=1.2):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        run = p.add_run()
        run.text = ln
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = FONT
    return tb


def add_bullets(slide, x, y, w, h, items, size=16, color=DARK,
                line_spacing=1.25, space_after=6):
    """items: list[str] 或 list[(str, dict)]，支持每条独立颜色/加粗。"""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        if isinstance(it, tuple):
            txt, style = it
        else:
            txt, style = it, {}
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = line_spacing
        p.space_after = Pt(space_after)
        # 项目符号
        r0 = p.add_run(); r0.text = "▪ "
        r0.font.size = Pt(style.get("size", size))
        r0.font.bold = True
        r0.font.color.rgb = style.get("color", BLUE)
        r0.font.name = FONT
        r = p.add_run(); r.text = txt
        r.font.size = Pt(style.get("size", size))
        r.font.bold = style.get("bold", False)
        r.font.color.rgb = style.get("color", color)
        r.font.name = FONT
    return tb


def add_title_bar(slide, title, subtitle=None):
    """顶部标题栏：蓝色装饰条 + 标题。"""
    add_rect(slide, 0, 0, prs.slide_width, Inches(1.05), BLUE)
    add_rect(slide, 0, Inches(1.05), prs.slide_width, Inches(0.06), ORANGE)
    add_text(slide, Inches(0.55), Inches(0.18), Inches(12.2), Inches(0.8),
             title, size=26, color=WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    if subtitle:
        add_text(slide, Inches(0.55), Inches(1.15), Inches(12.2), Inches(0.4),
                 subtitle, size=12, color=GREY)


def add_footer(slide, idx):
    add_text(slide, Inches(12.3), Inches(7.05), Inches(0.9), Inches(0.4),
             f"{idx}", size=10, color=GREY, align=PP_ALIGN.RIGHT)


def add_image(slide, path, x, y, w=None, h=None):
    return slide.shapes.add_picture(path, x, y, width=w, height=h)


def kpi_card(slide, x, y, w, h, value, label, color=BLUE):
    """统计卡片：大数值 + 标签。"""
    card = add_rect(slide, x, y, w, h, LIGHT)
    add_text(slide, x, y + Inches(0.08), w, Inches(0.6), value,
             size=24, color=color, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, x, y + Inches(0.66), w, Inches(0.4), label,
             size=11, color=GREY, align=PP_ALIGN.CENTER)
    return card


# ===========================================================================
# 1. 封面
# ===========================================================================
s = add_slide()
add_rect(s, 0, 0, prs.slide_width, prs.slide_height, BLUE)
add_rect(s, 0, Inches(4.6), prs.slide_width, Inches(0.06), ORANGE)
add_text(s, Inches(0.9), Inches(1.5), Inches(11.5), Inches(1.6),
         "开源技术采纳率预测与竞争力归因研究", size=40, color=WHITE, bold=True)
add_text(s, Inches(0.9), Inches(2.6), Inches(11.5), Inches(1.2),
         "——「不足与后续工作」进展汇报", size=28, color=RGBColor(0xDD, 0xE7, 0xF2))
add_text(s, Inches(0.9), Inches(4.9), Inches(11.5), Inches(1.8),
         "汇报人：黄恺祺\n南京大学 计算机科学与技术系", size=16, color=WHITE, line_spacing=1.5)
add_text(s, Inches(0.9), Inches(6.6), Inches(11.5), Inches(0.6),
         "基于 Stack Overflow 2018–2022 真实开发者调查数据", size=13,
         color=RGBColor(0xBB, 0xCE, 0xE2))

# ===========================================================================
# 2. 回顾：上次工作与遗留问题
# ===========================================================================
s = add_slide()
add_title_bar(s, "一、回顾：上次工作与五项遗留问题")
add_text(s, Inches(0.55), Inches(1.45), Inches(12.2), Inches(1.5),
         "上次核心结论（基于合规模拟面板数据）", size=17, color=BLUE, bold=True)
add_bullets(s, Inches(0.55), Inches(2.1), Inches(12.2), Inches(1.6), [
    "采纳惯性 β1≈0.80 + 渴望转化率 β2≈0.23，仅两变量即可解释 98.9% 的采纳率变化",
    "「渴望缺口」= 渴望率 − 使用率，识别 Rust/Go（净流入）与 JavaScript/HTML/CSS（净流出）",
], size=14, space_after=4)

add_text(s, Inches(0.55), Inches(3.75), Inches(12.2), Inches(0.5),
         "上次明确提出的「不足与后续工作」（本次逐项完成）", size=17, color=BLUE, bold=True)
add_bullets(s, Inches(0.55), Inches(4.3), Inches(12.2), Inches(2.9), [
    ("短期 ① 用真实多年份调查数据替换模拟数据，验证 β1≈0.80 / β2≈0.23", {"color": GREEN}),
    ("短期 ② 引入 SHAP 值，量化「渴望缺口」对单项技术预测的贡献", {"color": GREEN}),
    ("中期 ③ 将迁移网络的 PageRank / 社区划分等图特征纳入随机森林", {"color": ORANGE}),
    ("中期 ④ 尝试 XGBoost / LightGBM，与随机森林横向对比", {"color": ORANGE}),
    ("长期 ⑤ 构建「存量-增量-口碑」三维动态预警系统", {"color": RED}),
], size=15, space_after=10)
add_footer(s, 2)

# ===========================================================================
# 3. 数据
# ===========================================================================
s = add_slide()
add_title_bar(s, "二、数据：获取真实多年份调查数据")
add_text(s, Inches(0.55), Inches(1.35), Inches(12.2), Inches(0.5),
         "数据源与处理", size=17, color=BLUE, bold=True)
add_bullets(s, Inches(0.55), Inches(1.95), Inches(12.2), Inches(2.0), [
    "Stack Overflow 官方年度开发者调查 2018–2022（公开可下载），共 5 年、约 38 万名受访者",
    "统一抽取四大领域（语言/数据库/平台/Web框架）的「已使用」与「想使用」列，处理 2020→2021 年列名变更",
    "计算每项技术的 usage / desire / admiration，构建「技术 × 年份」面板，并生成滞后特征",
], size=14, space_after=6)
kpi_card(s, Inches(0.9), Inches(4.35), Inches(3.6), Inches(1.5), "159 项技术", "覆盖四大技术领域", BLUE)
kpi_card(s, Inches(4.9), Inches(4.35), Inches(3.6), Inches(1.5), "253 条样本", "含完整滞后特征的建模样本", ORANGE)
kpi_card(s, Inches(8.9), Inches(4.35), Inches(3.6), Inches(1.5), "4 个年度转移", "2019–2022 逐年前向预测", GREEN)
add_text(s, Inches(0.9), Inches(6.15), Inches(11.6), Inches(0.8),
         "注：2016/2017 数据托管与题目格式差异较大，2023/2024 需网页表单下载，故本阶段采用口径一致的 2018–2022 五年窗口；"
         "代码已支持一键扩展到更多年份。", size=11, color=GREY, line_spacing=1.3)
add_footer(s, 3)

# ===========================================================================
# 4. 结果1：真实数据验证
# ===========================================================================
s = add_slide()
add_title_bar(s, "三、结果 ①：真实数据几乎完美复现 β1 / β2")
add_bullets(s, Inches(0.55), Inches(1.3), Inches(12.3), Inches(1.9), [
    ("真实数据回归：β1(采纳惯性)=0.8033，β2(渴望转化率)=0.2415，R²=0.9562", {"bold": True, "size": 16}),
    ("对比模拟设定 0.80 / 0.23：β1 偏差仅 +0.42%，β2 偏差 +4.99%——原论文的模拟参数高度符合真实采纳动力学", {"color": GREEN}),
    ("年份固定效应稳健性检验：β1=0.8024、β2=0.2430，结论不变", {}),
], size=14, space_after=5)
add_image(s, os.path.join(FIG_DIR, "03_regression_validation.png"),
          Inches(0.55), Inches(3.25), w=Inches(12.3))
add_footer(s, 4)

# ===========================================================================
# 5. 结果1b：分领域异质性
# ===========================================================================
s = add_slide()
add_title_bar(s, "三、结果 ①（续）：分领域异质性")
add_text(s, Inches(0.55), Inches(1.35), Inches(12.2), Inches(0.5),
         "「惯性 vs 意愿」在不同技术赛道中差异显著", size=17, color=BLUE, bold=True)
# 手工表
table_data = [
    ("领域", "β1 采纳惯性", "β2 渴望转化率", "R²", "解读"),
    ("数据库", "0.898", "0.128", "0.970", "惯性最强、最稳定"),
    ("编程语言", "0.847", "0.167", "0.986", "存量基本盘牢固"),
    ("Web 框架", "0.744", "0.292", "0.945", "更新换代更快"),
    ("平台工具", "0.685", "0.375", "0.835", "最受意愿/趋势驱动"),
]
tbl_x, tbl_y, tbl_w, tbl_h = Inches(0.9), Inches(2.0), Inches(11.5), Inches(3.2)
rows, cols = len(table_data), len(table_data[0])
tbl = s.shapes.add_table(rows, cols, tbl_x, tbl_y, tbl_w, tbl_h).table
tbl.columns[0].width = Inches(1.9)
tbl.columns[1].width = Inches(2.3)
tbl.columns[2].width = Inches(2.3)
tbl.columns[3].width = Inches(1.6)
tbl.columns[4].width = Inches(3.4)
for i, row in enumerate(table_data):
    for j, val in enumerate(row):
        cell = tbl.cell(i, j)
        cell.text = val
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        for run in p.runs:
            run.font.name = FONT
            run.font.size = Pt(14)
            run.font.color.rgb = WHITE if i == 0 else DARK
            run.font.bold = (i == 0)
        cell.fill.solid()
        cell.fill.fore_color.rgb = BLUE if i == 0 else (LIGHT if i % 2 else WHITE)
add_text(s, Inches(0.9), Inches(5.5), Inches(11.5), Inches(1.2),
         "启示：「80/23」是全局均值，而非放之四海皆准——平台与框架类技术更依赖增量意愿，\n"
         "数据库与语言类技术更依赖存量惯性。技术选型时应结合赛道调整判断权重。",
         size=13, color=GREY, line_spacing=1.4)
add_footer(s, 5)

# ===========================================================================
# 6. 结果2：SHAP
# ===========================================================================
s = add_slide()
add_title_bar(s, "四、结果 ②：SHAP 归因——量化「渴望缺口」贡献")
add_bullets(s, Inches(0.55), Inches(1.3), Inches(12.3), Inches(1.9), [
    ("测试集 R²=0.9645；SHAP 显示「历史惯性 t-1」贡献 0.1345，占绝对主导", {"bold": True, "size": 16}),
    ("「渴望率/渴望缺口」类特征合计 SHAP 占比约 4.79%——证实原论文的「时间窗口稀释效应」", {"color": ORANGE}),
    ("渴望率虽占比小，但在回归中独立统计显著（β2=0.24），两者回答不同问题", {}),
], size=14, space_after=5)
add_image(s, os.path.join(FIG_DIR, "04_shap_importance.png"),
          Inches(0.55), Inches(3.3), w=Inches(6.0))
add_image(s, os.path.join(FIG_DIR, "04_shap_by_tech.png"),
          Inches(6.75), Inches(3.3), w=Inches(6.1))
add_footer(s, 6)

# ===========================================================================
# 7. 结果3：图特征
# ===========================================================================
s = add_slide()
add_title_bar(s, "五、结果 ③：迁移网络图特征提升预测精度")
add_bullets(s, Inches(0.55), Inches(1.3), Inches(12.3), Inches(1.6), [
    ("用训练年份受访者数据构建技术「共现网络」（138 节点、7364 条边）", {}),
    ("提取 PageRank、加权度、Louvain 社区标签三类图特征，并入随机森林", {}),
    ("测试集 R² 由 0.9656 提升至 0.9719（+0.0063），RMSE 由 0.0298 降至 0.0270", {"bold": True, "color": GREEN, "size": 16}),
], size=14, space_after=5)
add_image(s, os.path.join(FIG_DIR, "05_graph_features.png"),
          Inches(0.55), Inches(3.0), w=Inches(12.3))
add_footer(s, 7)

# ===========================================================================
# 8. 结果4：三模型对比
# ===========================================================================
s = add_slide()
add_title_bar(s, "六、结果 ④：三种集成模型横向对比")
add_text(s, Inches(0.55), Inches(1.35), Inches(12.2), Inches(0.5),
         "相同特征、相同时序切分下的测试集精度", size=17, color=BLUE, bold=True)
table_data = [
    ("模型", "R²", "RMSE", "MAE", "交叉验证 R²"),
    ("随机森林 RF", "0.9644", "0.0304", "0.0205", "0.8662"),
    ("XGBoost", "0.9610", "0.0318", "0.0196", "0.8297"),
    ("LightGBM", "0.9535", "0.0347", "0.0213", "0.7767"),
]
tbl_x, tbl_y, tbl_w, tbl_h = Inches(1.2), Inches(2.0), Inches(10.9), Inches(2.6)
tbl = s.shapes.add_table(len(table_data), 5, tbl_x, tbl_y, tbl_w, tbl_h).table
for j, w in enumerate([3.1, 2.2, 2.2, 2.2, 2.2]):
    tbl.columns[j].width = Inches(w)
for i, row in enumerate(table_data):
    for j, val in enumerate(row):
        cell = tbl.cell(i, j)
        cell.text = val
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        for run in p.runs:
            run.font.name = FONT
            run.font.size = Pt(15)
            run.font.color.rgb = WHITE if i == 0 else DARK
            run.font.bold = (i == 0)
        cell.fill.solid()
        cell.fill.fore_color.rgb = BLUE if i == 0 else (LIGHT if i % 2 else WHITE)
add_image(s, os.path.join(FIG_DIR, "06_boosting_comparison.png"),
          Inches(1.0), Inches(4.9), w=Inches(7.2))
add_text(s, Inches(8.5), Inches(5.1), Inches(4.3), Inches(1.6),
         "结论：\n小样本（253 条）场景下，随机森林仍是精度与稳定性最优的选择；\n"
         "梯度提升模型更依赖大数据量才能发挥优势。",
         size=13, color=DARK, line_spacing=1.35)
add_footer(s, 8)

# ===========================================================================
# 9. 结果5：预警系统
# ===========================================================================
s = add_slide()
add_title_bar(s, "七、结果 ⑤：「存量 × 增量 × 口碑」三维动态预警系统")
add_bullets(s, Inches(0.55), Inches(1.25), Inches(12.3), Inches(1.6), [
    ("规则：渴望缺口连续 2 年为负 → 自动触发「衰退预警」；连续 2 年为正 → 「增长信号」", {}),
    ("共 159 项技术：衰退预警 52 项 / 增长信号 34 项 / 观察稳定 73 项", {"bold": True}),
], size=14, space_after=5)
add_image(s, os.path.join(FIG_DIR, "07_early_warning.png"),
          Inches(0.55), Inches(2.75), w=Inches(7.6))
# 右侧文字小结
add_text(s, Inches(8.45), Inches(2.75), Inches(4.4), Inches(0.5),
         "衰退预警（示例）", size=15, color=RED, bold=True)
add_bullets(s, Inches(8.45), Inches(3.2), Inches(4.4), Inches(1.8), [
    "JavaScript 缺口 −0.21", "MySQL −0.20", "HTML/CSS −0.19",
    "jQuery −0.18", "SQL −0.15",
], size=13, color=DARK, space_after=3)
add_text(s, Inches(8.45), Inches(5.05), Inches(4.4), Inches(0.5),
         "增长信号（示例）", size=15, color=GREEN, bold=True)
add_bullets(s, Inches(8.45), Inches(5.5), Inches(4.4), Inches(1.6), [
    "Rust 缺口 +0.148", "Kubernetes +0.145", "Go +0.107",
    "Docker +0.086", "Svelte +0.079",
], size=13, color=DARK, space_after=3)
add_footer(s, 9)

# ===========================================================================
# 10. 总结
# ===========================================================================
s = add_slide()
add_title_bar(s, "八、总结与展望")
add_bullets(s, Inches(0.55), Inches(1.35), Inches(12.3), Inches(4.6), [
    ("五项后续工作已全部完成并给出可复现代码（run_all.py 一键运行）", {"bold": True, "size": 16}),
    ("核心发现：真实数据几乎完美复现 β1≈0.80 / β2≈0.23，模拟设定经受住了真实检验", {"color": GREEN}),
    ("SHAP 证实「时间窗口稀释效应」；图特征使 R² 再提升 0.0063；小样本下随机森林仍最优", {}),
    ("三维预警系统可自动识别 52 项衰退预警技术（JavaScript/MySQL/HTML-CSS…）", {}),
    ("不足与后续：跨年技术名需进一步对齐（如 Bash/Shell 变体）；可接入 2023/2024 与图神经网络", {}),
], size=15, space_after=10)
add_footer(s, 10)

# ===========================================================================
# 11. 致谢
# ===========================================================================
s = add_slide()
add_rect(s, 0, 0, prs.slide_width, prs.slide_height, BLUE)
add_text(s, Inches(0.9), Inches(2.6), Inches(11.5), Inches(1.2),
         "感谢聆听，恳请各位老师同学批评指正！", size=36, color=WHITE, bold=True,
         align=PP_ALIGN.CENTER)
add_text(s, Inches(0.9), Inches(4.3), Inches(11.5), Inches(1.6),
         "数据：Stack Overflow Annual Developer Survey 2018–2022\n"
         "代码与结果：见「后续工作/」目录（README.md 附复现说明）",
         size=15, color=RGBColor(0xDD, 0xE7, 0xF2), align=PP_ALIGN.CENTER, line_spacing=1.6)

# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------
out = os.path.join(config.BASE_DIR, "组会汇报_不足与后续工作进展.pptx")
prs.save(out)
print(f"已生成 PPT：{out}")
