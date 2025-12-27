#!/usr/bin/env python3
# /// script
# dependencies = ["pillow"]
# ///

from PIL import Image, ImageDraw

def create_green_lightning_icon(filename, size):
    """創建綠色閃電圖示 - 透明背景"""
    # 創建透明背景圖片
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 閃電路徑座標
    scale = size / 64
    lightning_points = [
        (44 * scale, 2 * scale),   # 右上
        (16 * scale, 30 * scale),  # 左中上
        (28 * scale, 30 * scale),  # 中間橫線右
        (10 * scale, 62 * scale),  # 左下
        (48 * scale, 34 * scale),  # 右中下
        (36 * scale, 34 * scale),  # 中間橫線左
    ]

    # 綠色 (#4ADE80)
    green = (74, 222, 128, 255)

    # 畫閃電填充
    draw.polygon(lightning_points, fill=green)

    # 畫白色邊框讓輪廓更清楚
    draw.line(lightning_points + [lightning_points[0]], fill=(255, 255, 255, 255), width=int(2*scale))

    # 保存
    img.save(filename)
    print(f"✅ Created {filename} ({size}x{size}) - 綠色閃電 + 透明背景")

# 生成圖示
create_green_lightning_icon('icon.png', 64)
create_green_lightning_icon('icon-preview.png', 512)

print("\n✅ 綠色閃電圖示生成完成！")
