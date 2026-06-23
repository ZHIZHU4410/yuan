import os
import sys

def list_files(directory_path):
    """输出指定路径里的所有文件名称"""
    # 展开用户目录（如 ~）
    directory_path = os.path.expanduser(directory_path)

    if not os.path.exists(directory_path):
        print(f"错误：路径不存在 - {directory_path}")
        return

    if not os.path.isdir(directory_path):
        print(f"错误：路径不是目录 - {directory_path}")
        return

    print(f"\n{directory_path} 目录下的所有文件：")
    print("-" * 50)

    file_count = 0
    for entry in os.listdir(directory_path):
        full_path = os.path.join(directory_path, entry)
        if os.path.isfile(full_path):
            file_count += 1
            # 获取文件大小
            size = os.path.getsize(full_path)
            print(f"  {entry}  ({size:,} bytes)")

    print("-" * 50)
    print(f"共 {file_count} 个文件")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    else:
        target_path = input("请输入要列出文件的目录路径: ").strip()

    list_files(target_path)
