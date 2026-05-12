import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open(r'论文_unpacked\word\document.xml', encoding='utf-8') as f:
    xml = f.read()

# 找"图3-1"所在段落，以及它周边 2000 字符的完整 XML
idx = xml.find('图3-1')
print('图3-1位置:', idx)

# 显示前后各 2000 字符的原始 XML（找 drawing/image）
window = xml[idx-100:idx+3000]
print('=== 图3-1 附近原始XML ===')
print(window[:3000])
