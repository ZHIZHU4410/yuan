from pynput import mouse
import sys

def on_click(x, y, button, pressed):
    """鼠标点击回调"""
    if pressed:
        print(f"点击坐标 -> X: {x}, Y: {y}")
        # 可选择在点击后继续监听，按 Ctrl+C 退出
        # 如果想点击一次就退出，可以取消下面注释：
        # return False

def on_move(x, y):
    """鼠标移动实时显示（可选）"""
    # 实时显示当前坐标（会频繁刷新，可按需开启）
    # print(f"当前坐标: X: {x}, Y: {y}", end="\r")
    pass

def main():
    print("===== 鼠标坐标获取工具 =====")
    print("请在游戏窗口内点击任意位置，将输出该点屏幕坐标。")
    print("按 Ctrl+C 退出程序。\n")
    
    # 创建鼠标监听器
    with mouse.Listener(on_click=on_click, on_move=on_move) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            print("\n已退出。")
            sys.exit(0)

if __name__ == "__main__":
    main()