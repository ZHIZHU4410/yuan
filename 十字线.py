"""
全屏十字线脚本 - 获取当前屏幕分辨率，绘制 x/2 和 y/2 两条直线
修复：让窗口鼠标穿透，不影响正常操作
"""
import ctypes
import tkinter as tk


def make_click_through(hwnd: int) -> None:
    """设置窗口为鼠标穿透模式（点击事件传递到下层窗口）"""
    GWL_EXSTYLE = -20
    WS_EX_TRANSPARENT = 0x00000020

    ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(
        hwnd, GWL_EXSTYLE, ex_style | WS_EX_TRANSPARENT
    )
    print("已启用鼠标穿透模式")


def main():
    root = tk.Tk()
    root.title("十字线")

    # 获取屏幕分辨率
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    print(f"屏幕分辨率: {screen_width} x {screen_height}")

    # 计算中心线位置
    cx = screen_width // 2
    cy = screen_height // 2

    # 全屏无边框窗口
    root.geometry(f"{screen_width}x{screen_height}+0+0")
    root.overrideredirect(True)       # 无边框
    root.attributes("-topmost", True)  # 置顶

    # 设置透明色（使窗口背景透明）
    root.wm_attributes("-transparentcolor", "white")
    root.configure(bg="white")

    # 创建画布
    canvas = tk.Canvas(
        root,
        width=screen_width,
        height=screen_height,
        bg="white",
        highlightthickness=0,
    )
    canvas.pack()

    # 画垂直中线 x/2
    canvas.create_line(cx, 0, cx, screen_height, fill="red", width=2)

    # 画水平中线 y/2
    canvas.create_line(0, cy, screen_width, cy, fill="red", width=2)

    print(f"十字线已绘制：垂直线 x={cx}，水平线 y={cy}")

    # 先刷新窗口，确保 HWND 有效后启用鼠标穿透
    root.update_idletasks()
    make_click_through(root.winfo_id())

    # 按 Esc 退出
    root.bind("<Escape>", lambda e: root.destroy())

    root.mainloop()


if __name__ == "__main__":
    main()
