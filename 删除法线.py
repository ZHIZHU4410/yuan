import os
import glob

def main():
    # 手动输入文件目录
    directory = input("请输入文件目录路径：").strip()
    if not os.path.isdir(directory):
        print("输入的路径不是有效的目录。")
        return
    
    # 查找指定目录下所有以 _n.png 结尾的文件
    pattern = os.path.join(directory, "*_n.png")
    normal_files = glob.glob(pattern)
    
    if not normal_files:
        print("未找到任何法线图片（*_n.png）")
        return
    
    print("找到以下法线图片：")
    for f in normal_files:
        print(f"  {f}")
    
    # 请求确认
    confirm = input(f"\n确认删除以上 {len(normal_files)} 个文件吗？(y/n): ").strip().lower()
    if confirm == 'y':
        for f in normal_files:
            os.remove(f)
            print(f"已删除: {f}")
        print("删除完成。")
    else:
        print("操作已取消。")

if __name__ == "__main__":
    main()