#!/usr/bin/env python3
# /// script
# dependencies = ["pillow"]
# ///

from PIL import Image, ImageDraw

def create_lightning_icon(filename, size, color, bg_color=None):
    """創建閃電圖示"""
    # 創建圖片
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0) if bg_color is None else bg_color)
    draw = ImageDraw.Draw(img)

    # 如果有背景色，畫圓形背景
    if bg_color:
        draw.ellipse([2, 2, size-2, size-2], fill=bg_color)

    # 閃電路徑座標（比例調整）
    scale = size / 64
    lightning_points = [
        (44 * scale, 2 * scale),   # 右上
        (16 * scale, 30 * scale),  # 左中上
        (28 * scale, 30 * scale),  # 中間橫線右
        (10 * scale, 62 * scale),  # 左下
        (48 * scale, 34 * scale),  # 右中下
        (36 * scale, 34 * scale),  # 中間橫線左
    ]

    # 畫閃電
    draw.polygon(lightning_points, fill=color, outline=color)

    # 保存
    img.save(filename)
    print(f"✅ Created {filename} ({size}x{size})")

# 生成三種版本的圖示
print("正在生成圖示...")

# 1. 黑色閃電 (適合 template icon)
create_lightning_icon('icon-black.png', 512, (0, 0, 0, 255))

# 2. 白色閃電 (適合 template icon)
create_lightning_icon('icon-white.png', 512, (255, 255, 255, 255))

# 3. 彩色閃電 (綠色 + 深色背景)
create_lightning_icon('icon-color.png', 512, (74, 222, 128, 255), (31, 41, 55, 255))

# 生成 64x64 的最終版本
create_lightning_icon('icon.png', 64, (0, 0, 0, 255))

print("\n✅ 所有圖示生成完成！")
print("預覽大圖: icon-black.png, icon-white.png, icon-color.png (512x512)")
print("最終圖示: icon.png (64x64)")
