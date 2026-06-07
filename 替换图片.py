import os
import shutil
from pathlib import Path

def replace_all_png(template_path, target_dir, recursive=True):
    """
    将目标目录下所有 .png 文件的内容替换为模板图片
    """
    template = Path(template_path)
    if not template.is_file():
        raise FileNotFoundError(f"模板文件不存在: {template}")
    if template.suffix.lower() != '.png':
        raise ValueError("模板文件必须是 PNG 格式")

    target = Path(target_dir)
    if not target.is_dir():
        raise NotADirectoryError(f"目标路径不是有效目录: {target}")

    pattern = "**/*.png" if recursive else "*.png"
    replaced_count = 0

    for png_file in target.glob(pattern):
        try:
            shutil.copy2(template, png_file)  # 覆盖，同时保留元数据
            print(f"✓ 已替换: {png_file}")
            replaced_count += 1
        except Exception as e:
            print(f"✗ 替换失败: {png_file}，错误: {e}")

    print(f"\n完成！共替换 {replaced_count} 个 PNG 文件。")

def main():
    print("===== PNG 批量替换工具 =====")
    template = input("请输入模板 PNG 图片的完整路径: ").strip().strip('"')
    target_dir = input("请输入目标文件夹路径: ").strip().strip('"')
    
    # 是否包含子文件夹
    choice = input("是否包含子文件夹？(y/n，默认 y): ").strip().lower()
    recursive = choice != 'n'

    # 执行前二次确认
    print(f"\n将用模板: {template}")
    print(f"替换文件夹: {target_dir}")
    print(f"包含子文件夹: {'是' if recursive else '否'}")
    confirm = input("此操作不可逆，会直接覆盖所有 PNG 文件！确认继续？(y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消操作。")
        return

    try:
        replace_all_png(template, target_dir, recursive)
    except Exception as e:
        print(f"出错: {e}")

if __name__ == "__main__":
    main()