from PIL import Image
import os

# 当前目录
img_dir = os.path.dirname(__file__)
target_size = (1800, 1000)

for filename in os.listdir(img_dir):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        filepath = os.path.join(img_dir, filename)
        try:
            with Image.open(filepath) as img:
                img = img.convert("RGB")  # 保证统一色彩通道
                img_resized = img.resize(target_size)

                # 保存为 .png，保持同名但扩展名统一
                new_name = os.path.splitext(filename)[0] + ".png"
                new_path = os.path.join(img_dir, new_name)
                img_resized.save(new_path, format="PNG")
                print(f"✅ Resized: {filename} -> {new_name}")
        except Exception as e:
            print(f"❌ Failed to process {filename}: {e}")
