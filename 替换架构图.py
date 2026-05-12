import sys, re, shutil, os
sys.stdout.reconfigure(encoding='utf-8')

UNPACKED  = r'E:\360MoveData\Users\ASUS\Desktop\textworld\论文_unpacked'
DOC_XML   = os.path.join(UNPACKED, 'word', 'document.xml')
RELS_FILE = os.path.join(UNPACKED, 'word', '_rels', 'document.xml.rels')
MEDIA_DIR = os.path.join(UNPACKED, 'word', 'media')
NEW_IMG   = r'E:\360MoveData\Users\ASUS\Desktop\textworld\论文素材\图3-1_系统总体架构.png'

# ── 1. 找 rId12 对应的旧文件名 ───────────────────────────────
with open(RELS_FILE, encoding='utf-8') as f:
    rels = f.read()

m = re.search(r'<Relationship Id="rId12"[^>]*Target="media/([^"]+)"', rels)
if m:
    old_media = m.group(1)
    print(f'rId12 原文件: {old_media}')
else:
    print('未找到rId12，退出')
    sys.exit(1)

# ── 2. 复制新图，使用原文件名（直接覆盖）─────────────────────
old_path = os.path.join(MEDIA_DIR, old_media)
shutil.copy2(NEW_IMG, old_path)
print(f'已覆盖: {old_path}')
print(f'新文件大小: {os.path.getsize(old_path)/1024:.1f} KB')

# ── 3. 获取新图真实尺寸，计算 EMU ─────────────────────────────
from PIL import Image
img = Image.open(NEW_IMG)
w_px, h_px = img.size
print(f'新图尺寸: {w_px} x {h_px} px, DPI={img.info.get("dpi", "unknown")}')

# 目标宽度：13cm（论文版心宽约14cm）≈ 13 * 360000 EMU = 4680000 EMU (1 cm = 360000 EMU)
TARGET_W_CM = 13.0
emu_per_cm  = 360000
new_cx = int(TARGET_W_CM * emu_per_cm)        # 4680000
new_cy = int(new_cx * h_px / w_px)             # 等比
print(f'新图 EMU: cx={new_cx}, cy={new_cy}')
print(f'新图尺寸: {new_cx/360000:.1f}cm x {new_cy/360000:.1f}cm')

# ── 4. 修改 document.xml 中的 cx/cy ─────────────────────────
with open(DOC_XML, encoding='utf-8') as f:
    xml = f.read()

# 找到 rId12 的 drawing 块，更新 wp:extent 和 a:ext
# 策略：找到 r:embed="rId12" 所在的 drawing 块，用正则替换
def update_drawing_size(xml_str, rid, new_cx, new_cy):
    # 找含有该 rid 的 drawing 段落
    rid_idx = xml_str.find(f'r:embed="{rid}"')
    if rid_idx < 0:
        print(f'未找到 r:embed="{rid}"')
        return xml_str
    # 从 rid_idx 往前找 <wp:inline
    inline_start = xml_str.rfind('<wp:inline', 0, rid_idx)
    inline_end   = xml_str.find('</wp:inline>', rid_idx) + 13
    inline_block = xml_str[inline_start:inline_end]

    # 替换 wp:extent
    inline_block = re.sub(
        r'(<wp:extent cx=")[^"]+(" cy=")[^"]+"',
        lambda m2: f'<wp:extent cx="{new_cx}" cy="{new_cy}"',
        inline_block
    )
    # 替换 a:ext (spPr 里的)
    inline_block = re.sub(
        r'(<a:ext cx=")[^"]+(" cy=")[^"]+"',
        lambda m2: f'<a:ext cx="{new_cx}" cy="{new_cy}"',
        inline_block
    )
    return xml_str[:inline_start] + inline_block + xml_str[inline_end:]

xml = update_drawing_size(xml, 'rId12', new_cx, new_cy)

with open(DOC_XML, 'w', encoding='utf-8') as f:
    f.write(xml)
print('document.xml 图片尺寸已更新')

# ── 5. 重新打包 docx ────────────────────────────────────────
import zipfile

output = r'E:\360MoveData\Users\ASUS\Desktop\textworld\论文（修改版v2）.docx'
unpacked = UNPACKED

with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(unpacked):
        for file in files:
            filepath = os.path.join(root, file)
            arcname  = os.path.relpath(filepath, unpacked)
            zf.write(filepath, arcname)

size = os.path.getsize(output)
print(f'\n打包完成: {output}')
print(f'文件大小: {size/1024:.1f} KB')
