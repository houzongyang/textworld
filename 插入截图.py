#!/usr/bin/env python3
"""将游戏运行截图插入到论文中的4.5系统启动实现部分"""
import re, sys, os, shutil
sys.stdout.reconfigure(encoding='utf-8')

UNPACKED = r'E:\360MoveData\Users\ASUS\Desktop\textworld\论文_unpacked'
DOC_XML = os.path.join(UNPACKED, 'word', 'document.xml')
MEDIA_DIR = os.path.join(UNPACKED, 'word', 'media')
RELS_FILE = os.path.join(UNPACKED, 'word', '_rels', 'document.xml.rels')
CT_FILE = os.path.join(UNPACKED, '[Content_Types].xml')
SRC_DIR = r'E:\360MoveData\Users\ASUS\Desktop\textworld\论文素材'

# 1. 复制图片到媒体目录
img_map = [
    ('图4-2_系统首页.png', 'image29.png'),
    ('图4-3_场景与难度选择页面.png', 'image30.png'),
    ('图4-4_游戏运行页面.png', 'image31.png'),
]

for src_name, dst_name in img_map:
    src = os.path.join(SRC_DIR, src_name)
    dst = os.path.join(MEDIA_DIR, dst_name)
    shutil.copy2(src, dst)
    print(f'已复制: {src_name} -> {dst_name}')

# 2. 添加关系到 document.xml.rels
with open(RELS_FILE, encoding='utf-8') as f:
    rels = f.read()

existing_ids = [int(m.group(1)) for m in re.finditer(r'rId(\d+)', rels)]
next_id = max(existing_ids) + 1 if existing_ids else 100

rids = {}
new_rels_lines = []
for i, (_, dst_name) in enumerate(img_map):
    rid = f'rId{next_id}'
    rids[i] = rid
    new_rels_lines.append(
        f'<Relationship Id="{rid}" '
        f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
        f'Target="media/{dst_name}"/>'
    )
    print(f'添加关系: {rid} -> {dst_name}')
    next_id += 1

rels = rels.replace('</Relationships>', '\n'.join(new_rels_lines) + '\n</Relationships>')
with open(RELS_FILE, 'w', encoding='utf-8') as f:
    f.write(rels)
print('rels 已更新')

# 3. 确保 Content_Types.xml 包含 png 类型
with open(CT_FILE, encoding='utf-8') as f:
    ct = f.read()
if 'Extension="png"' not in ct:
    ct = ct.replace('</Types>', '<Default Extension="png" ContentType="image/png"/>\n</Types>')
    with open(CT_FILE, 'w', encoding='utf-8') as f:
        f.write(ct)
    print('Content_Types.xml 已更新')
else:
    print('Content_Types.xml 已包含 png 类型')

# 4. 获取图片实际尺寸（EMU单位，9144000 EMU/m，1英寸=914400 EMU）
from PIL import Image

def get_image_emu(path, max_width_emu=5486400):  # 最大宽度约6cm
    try:
        img = Image.open(path)
        w, h = img.size  # pixels
        # 按72 DPI转换（Word默认），1 inch = 914400 EMU，72 dpi -> 12700 EMU/px
        # 但更通用方式：固定最大宽度，等比缩放
        # 实际上用固定宽度比较好
        emu_w = max_width_emu
        emu_h = int(h * max_width_emu / w)
        return emu_w, emu_h
    except Exception:
        return 5486400, 3086325  # 默认 6cm x 3.37cm

# 5. 构建图片段落 XML
def make_image_para(rid, emu_w, emu_h, img_name, caption, pic_id):
    return f'''    <w:p w14:paraId="CC{pic_id:04X}AB" w14:textId="77777777" w:rsidR="00DD1234" w:rsidRDefault="00DD1234">
      <w:pPr>
        <w:jc w:val="center"/>
      </w:pPr>
      <w:r>
        <w:rPr><w:noProof/></w:rPr>
        <w:drawing>
          <wp:inline distT="0" distB="0" distL="0" distR="0" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
            <wp:extent cx="{emu_w}" cy="{emu_h}"/>
            <wp:effectExtent l="0" t="0" r="0" b="0"/>
            <wp:docPr id="{pic_id}" name="{img_name}"/>
            <wp:cNvGraphicFramePr>
              <a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>
            </wp:cNvGraphicFramePr>
            <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
              <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
                <pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
                  <pic:nvPicPr>
                    <pic:cNvPr id="{pic_id}" name="{img_name}"/>
                    <pic:cNvPicPr><a:picLocks noChangeAspect="1" noChangeArrowheads="1"/></pic:cNvPicPr>
                  </pic:nvPicPr>
                  <pic:blipFill>
                    <a:blip r:embed="{rid}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>
                    <a:stretch><a:fillRect/></a:stretch>
                  </pic:blipFill>
                  <pic:spPr bwMode="auto">
                    <a:xfrm><a:off x="0" y="0"/><a:ext cx="{emu_w}" cy="{emu_h}"/></a:xfrm>
                    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                    <a:noFill/>
                  </pic:spPr>
                </pic:pic>
              </a:graphicData>
            </a:graphic>
          </wp:inline>
        </w:drawing>
      </w:r>
    </w:p>
    <w:p w14:paraId="CC{pic_id:04X}CD" w14:textId="77777777" w:rsidR="00DD1234" w:rsidRDefault="00DD1234">
      <w:pPr>
        <w:jc w:val="center"/>
        <w:rPr>
          <w:rFonts w:ascii="宋体" w:eastAsia="宋体" w:hAnsi="宋体"/>
          <w:sz w:val="20"/>
          <w:szCs w:val="20"/>
        </w:rPr>
      </w:pPr>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="宋体" w:eastAsia="宋体" w:hAnsi="宋体" w:hint="eastAsia"/>
          <w:sz w:val="20"/>
          <w:szCs w:val="20"/>
        </w:rPr>
        <w:t>{caption}</w:t>
      </w:r>
    </w:p>'''

# 计算图片尺寸
screenshots = [
    (rids[0], os.path.join(SRC_DIR, '图4-2_系统首页.png'), '图4-23a 系统首页界面', 'screenshot_a', 2001),
    (rids[1], os.path.join(SRC_DIR, '图4-3_场景与难度选择页面.png'), '图4-23b 场景与难度选择页面', 'screenshot_b', 2002),
    (rids[2], os.path.join(SRC_DIR, '图4-4_游戏运行页面.png'), '图4-23c 游戏运行页面', 'screenshot_c', 2003),
]

# 读取 XML
with open(DOC_XML, encoding='utf-8') as f:
    xml = f.read()

# 找到图4-23 浏览器界面位置
idx_423 = xml.find('图4-23 浏览器界面')
if idx_423 < 0:
    print('未找到图4-23标记，搜索系统启动实现...')
    idx_423 = xml.find('图4-23')
print(f'图4-23位置: {idx_423}')

if idx_423 > 0:
    # 找到这整个段落（说明行）
    p_start = xml.rfind('<w:p ', 0, idx_423)
    p_end = xml.find('</w:p>', idx_423) + 6

    # 找到前一个段落（drawing段落）
    para_pattern = re.compile(r'<w:p [^>]+>.*?</w:p>', re.DOTALL)
    prev_matches = list(para_pattern.finditer(xml, max(0, p_start - 3000), p_start))
    if prev_matches and '<w:drawing' in prev_matches[-1].group():
        replace_start = prev_matches[-1].start()
    else:
        replace_start = p_start

    # 构建替换内容
    new_paras = []
    for rid, img_path, caption, img_name, pic_id in screenshots:
        emu_w, emu_h = get_image_emu(img_path)
        new_paras.append(make_image_para(rid, emu_w, emu_h, img_name, caption, pic_id))

    replacement = '\n'.join(new_paras)
    xml = xml[:replace_start] + replacement + xml[p_end:]
    print('截图段落插入完成')
else:
    print('警告：未找到图4-23，跳过截图插入')

# 写回
with open(DOC_XML, 'w', encoding='utf-8') as f:
    f.write(xml)
print('document.xml 截图部分已保存')
