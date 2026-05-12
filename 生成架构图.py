#!/usr/bin/env python3
"""生成系统总体架构图（图3-1），清晰替换论文中的模糊截图"""
import matplotlib
matplotlib.rcParams['font.family'] = ['Microsoft YaHei', 'SimHei', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(14, 10))
ax.set_xlim(0, 14)
ax.set_ylim(0, 10)
ax.axis('off')

# ── 颜色方案 ──────────────────────────────────────────────
LAYER_COLORS = {
    'env':     '#D6EAF8',   # 蓝
    'game':    '#D5F5E3',   # 绿
    'web':     '#FCF3CF',   # 黄
    'front':   '#FADBD8',   # 红
}
BORDER_COLORS = {
    'env':  '#2E86C1',
    'game': '#1E8449',
    'web':  '#B7950B',
    'front':'#CB4335',
}
LABEL_BG   = '#F0F3F4'
ARROW_COL  = '#566573'

def draw_layer(ax, y_bottom, height, facecolor, edgecolor, layer_label, sublabels, label_x=0.25):
    """绘制一个层次矩形，左侧纵向标签，右侧子模块"""
    # 主背景框
    rect = FancyBboxPatch((0.4, y_bottom), 13.2, height,
                          boxstyle="round,pad=0.05",
                          facecolor=facecolor, edgecolor=edgecolor, linewidth=2.0, zorder=2)
    ax.add_patch(rect)
    # 左侧竖向层名称标签
    label_rect = FancyBboxPatch((0.4, y_bottom), 1.4, height,
                                boxstyle="round,pad=0.02",
                                facecolor=edgecolor, edgecolor=edgecolor, linewidth=1.2, zorder=3)
    ax.add_patch(label_rect)
    ax.text(1.1, y_bottom + height / 2, layer_label,
            ha='center', va='center', fontsize=13, fontweight='bold',
            color='white', rotation=90, zorder=4)
    return

def draw_module(ax, x, y, w, h, text, facecolor='#FDFEFE', edgecolor='#717D7E',
                fontsize=10.5, bold=False, text_color='#1B2631'):
    """绘制子模块方块"""
    rect = FancyBboxPatch((x, y), w, h,
                          boxstyle="round,pad=0.06",
                          facecolor=facecolor, edgecolor=edgecolor, linewidth=1.5, zorder=5)
    ax.add_patch(rect)
    fw = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text,
            ha='center', va='center', fontsize=fontsize,
            fontweight=fw, color=text_color, zorder=6, wrap=True)

def draw_arrow(ax, x1, y1, x2, y2, label=''):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=ARROW_COL,
                                lw=1.8, connectionstyle='arc3,rad=0.0'),
                zorder=7)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx+0.1, my, label, fontsize=8.5, color=ARROW_COL, va='center', zorder=8)

# ════════════════════════════════════════════════════════════
# 层 1 – 前端交互层  (最上，y=7.5~9.3)
# ════════════════════════════════════════════════════════════
draw_layer(ax, 7.5, 1.7, LAYER_COLORS['front'], BORDER_COLORS['front'],
           '前端交互层', [])
# 子模块
draw_module(ax, 2.1, 7.85, 2.6, 0.9, '主题选择页面\n(HTML+CSS+JS)',
            facecolor='#FADBD8', edgecolor=BORDER_COLORS['front'], fontsize=10)
draw_module(ax, 5.1, 7.85, 2.6, 0.9, '游戏交互页面\n(命令输入/反馈展示)',
            facecolor='#FADBD8', edgecolor=BORDER_COLORS['front'], fontsize=10)
draw_module(ax, 8.1, 7.85, 2.6, 0.9, '结果展示页面\n(得分/通关状态)',
            facecolor='#FADBD8', edgecolor=BORDER_COLORS['front'], fontsize=10)
draw_module(ax, 11.1, 7.85, 1.8, 0.9, '浏览器\n(Chrome等)',
            facecolor='#FADBD8', edgecolor=BORDER_COLORS['front'], fontsize=10)

# ════════════════════════════════════════════════════════════
# 双向箭头 前端↔Web  (y~7.5)
# ════════════════════════════════════════════════════════════
for cx in [3.4, 6.4, 9.4]:
    ax.annotate('', xy=(cx, 6.85), xytext=(cx, 7.85),
                arrowprops=dict(arrowstyle='<->', color=ARROW_COL, lw=1.8), zorder=7)
ax.text(6.9, 7.35, 'HTTP / AJAX 请求-响应', ha='center', va='center',
        fontsize=9, color=ARROW_COL, zorder=8,
        bbox=dict(facecolor='white', edgecolor='none', alpha=0.8))

# ════════════════════════════════════════════════════════════
# 层 2 – Web服务层  (y=5.3~6.9)
# ════════════════════════════════════════════════════════════
draw_layer(ax, 5.3, 1.55, LAYER_COLORS['web'], BORDER_COLORS['web'],
           'Web服务层', [])
draw_module(ax, 2.1, 5.6, 2.6, 0.85, 'Flask 路由\n(/start /command /hint)',
            facecolor='#FCF3CF', edgecolor=BORDER_COLORS['web'], fontsize=10)
draw_module(ax, 5.1, 5.6, 2.6, 0.85, '会话管理\n(Session / game_id)',
            facecolor='#FCF3CF', edgecolor=BORDER_COLORS['web'], fontsize=10)
draw_module(ax, 8.1, 5.6, 2.6, 0.85, 'JSON 序列化\n(请求解析/结果封装)',
            facecolor='#FCF3CF', edgecolor=BORDER_COLORS['web'], fontsize=10)
draw_module(ax, 11.1, 5.6, 1.8, 0.85, '静态资源\n(templates/)',
            facecolor='#FCF3CF', edgecolor=BORDER_COLORS['web'], fontsize=10)

# ════════════════════════════════════════════════════════════
# 双向箭头 Web↔游戏逻辑  (y~5.3)
# ════════════════════════════════════════════════════════════
for cx in [3.4, 6.4, 9.4]:
    ax.annotate('', xy=(cx, 4.65), xytext=(cx, 5.6),
                arrowprops=dict(arrowstyle='<->', color=ARROW_COL, lw=1.8), zorder=7)
ax.text(6.9, 5.15, '函数调用 / 游戏状态返回', ha='center', va='center',
        fontsize=9, color=ARROW_COL, zorder=8,
        bbox=dict(facecolor='white', edgecolor='none', alpha=0.8))

# ════════════════════════════════════════════════════════════
# 层 3 – 游戏逻辑层  (y=3.1~4.7)
# ════════════════════════════════════════════════════════════
draw_layer(ax, 3.1, 1.55, LAYER_COLORS['game'], BORDER_COLORS['game'],
           '游戏逻辑层', [])
draw_module(ax, 2.1, 3.4, 2.6, 0.85, '菜谱做菜模块\n(场景/物品/规则)',
            facecolor='#D5F5E3', edgecolor=BORDER_COLORS['game'], fontsize=10)
draw_module(ax, 5.1, 3.4, 2.6, 0.85, '防范火灾模块\n(隐患/灭火/逃生)',
            facecolor='#D5F5E3', edgecolor=BORDER_COLORS['game'], fontsize=10)
draw_module(ax, 8.1, 3.4, 2.6, 0.85, '垃圾分类模块\n(物品/投放/判定)',
            facecolor='#D5F5E3', edgecolor=BORDER_COLORS['game'], fontsize=10)
draw_module(ax, 11.1, 3.4, 1.8, 0.85, 'TextWorld\n框架引擎',
            facecolor='#A9DFBF', edgecolor=BORDER_COLORS['game'], fontsize=10, bold=True)

# ════════════════════════════════════════════════════════════
# 箭头 游戏逻辑↔运行环境
# ════════════════════════════════════════════════════════════
for cx in [3.4, 6.4, 9.4, 12.0]:
    ax.annotate('', xy=(cx, 2.45), xytext=(cx, 3.4),
                arrowprops=dict(arrowstyle='<->', color=ARROW_COL, lw=1.8), zorder=7)
ax.text(6.9, 2.95, '进程调用 / 依赖加载', ha='center', va='center',
        fontsize=9, color=ARROW_COL, zorder=8,
        bbox=dict(facecolor='white', edgecolor='none', alpha=0.8))

# ════════════════════════════════════════════════════════════
# 层 4 – 运行环境层  (y=0.8~2.5)
# ════════════════════════════════════════════════════════════
draw_layer(ax, 0.8, 1.65, LAYER_COLORS['env'], BORDER_COLORS['env'],
           '运行环境层', [])
draw_module(ax, 2.1, 1.1, 2.6, 0.95, 'Windows 主机\n(宿主操作系统)',
            facecolor='#D6EAF8', edgecolor=BORDER_COLORS['env'], fontsize=10)
draw_module(ax, 5.1, 1.1, 2.6, 0.95, 'WSL 2\n(Windows Subsystem for Linux)',
            facecolor='#D6EAF8', edgecolor=BORDER_COLORS['env'], fontsize=10)
draw_module(ax, 8.1, 1.1, 2.6, 0.95, 'Ubuntu 环境\n(Python 3 / pip 依赖)',
            facecolor='#D6EAF8', edgecolor=BORDER_COLORS['env'], fontsize=10)
draw_module(ax, 11.1, 1.1, 1.8, 0.95, 'TextWorld\n运行时',
            facecolor='#AED6F1', edgecolor=BORDER_COLORS['env'], fontsize=10, bold=True)

# ════════════════════════════════════════════════════════════
# 标题
# ════════════════════════════════════════════════════════════
ax.text(7, 9.72, '图3-1  系统总体架构', ha='center', va='center',
        fontsize=15, fontweight='bold', color='#1B2631', zorder=10)

# ════════════════════════════════════════════════════════════
# 图例
# ════════════════════════════════════════════════════════════
legend_items = [
    mpatches.Patch(facecolor=LAYER_COLORS['front'], edgecolor=BORDER_COLORS['front'], label='前端交互层'),
    mpatches.Patch(facecolor=LAYER_COLORS['web'],   edgecolor=BORDER_COLORS['web'],   label='Web服务层'),
    mpatches.Patch(facecolor=LAYER_COLORS['game'],  edgecolor=BORDER_COLORS['game'],  label='游戏逻辑层'),
    mpatches.Patch(facecolor=LAYER_COLORS['env'],   edgecolor=BORDER_COLORS['env'],   label='运行环境层'),
]
ax.legend(handles=legend_items, loc='lower right', fontsize=9.5,
          framealpha=0.9, bbox_to_anchor=(0.99, 0.01))

plt.tight_layout(pad=0.3)
out = r'E:\360MoveData\Users\ASUS\Desktop\textworld\论文素材\图3-1_系统总体架构.png'
plt.savefig(out, dpi=200, bbox_inches='tight', facecolor='white')
print(f'已保存: {out}')
import os
print(f'文件大小: {os.path.getsize(out)/1024:.1f} KB')
