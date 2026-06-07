import tkinter as tk
from tkinter import ttk
import threading
import time
import pyautogui
from pynput import keyboard

class GenshinDialogueSkipper:
    def __init__(self, root):
        self.root = root
        self.root.title("原神剧情跳过助手")
        self.root.geometry("350x250")
        self.root.attributes("-topmost", True)  # 保持窗口置顶，方便在游戏内查看状态

        # 状态控制
        self.running = False
        self.stop_event = threading.Event()
        self.listener = None

        # 参数设置
        self.space_interval = 0.2  # 按空格的间隔（秒）
        self.click_interval = 1.5  # 点击选项的间隔（秒）

        self.create_widgets()
        self.start_hotkey_listener()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="✨ 原神自动过剧情助手 ✨", font=("Microsoft YaHei", 12, "bold")).pack(pady=(0, 15))

        ttk.Label(frame, text="工作原理: 自动按空格 + 自动点右侧选项").pack()
        ttk.Label(frame, text="快捷键: 【 F9 】 启动 / 停止").pack(pady=10)

        self.status_lbl = ttk.Label(frame, text="⚫ 状态: 休息中...", foreground="gray", font=("Microsoft YaHei", 12, "bold"))
        self.status_lbl.pack(pady=15)

        ttk.Label(frame, text="⚠️ 提示: 请确保游戏处于“无边框窗口”模式\n如需停止，再按一次 F9 即可", foreground="#888888").pack(side=tk.BOTTOM)

    def start_hotkey_listener(self):
        # 监听 F9 键
        def on_press(key):
            if key == keyboard.Key.f9:
                self.toggle_script()
        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.start()

    def toggle_script(self):
        if self.running:
            self.running = False
            self.stop_event.set()
            self.root.after(0, lambda: self.status_lbl.config(text="⚫ 状态: 已停止", foreground="gray"))
        else:
            self.running = True
            self.stop_event.clear()
            self.root.after(0, lambda: self.status_lbl.config(text="🟢 状态: 狂按空格中...", foreground="green"))
            threading.Thread(target=self.skip_loop, daemon=True).start()

    def skip_loop(self):
        # 获取屏幕分辨率，动态计算对话选项大概出现的位置 (通常在屏幕靠右 3/4，偏下位置)
        screen_width, screen_height = pyautogui.size()
        option_x = int(screen_width * 0.72)
        option_y = int(screen_height * 0.65)

        last_click_time = time.time()

        while not self.stop_event.is_set() and self.running:
            # 1. 狂按空格键（推进普通对话）
            pyautogui.press('space', _pause=False)
            
            # 2. 每隔一段时间，鼠标移动到右侧并点击（选择对话分支）
            current_time = time.time()
            if current_time - last_click_time > self.click_interval:
                # 记录鼠标当前位置
                orig_x, orig_y = pyautogui.position()
                
                # 瞬移过去点击并瞬间移回来，尽量不影响你偶尔的鼠标操作
                pyautogui.click(x=option_x, y=option_y, _pause=False)
                pyautogui.moveTo(orig_x, orig_y, _pause=False)
                
                last_click_time = current_time

            time.sleep(self.space_interval)

    def on_close(self):
        self.running = False
        self.stop_event.set()
        if self.listener:
            self.listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    # 关闭 pyautogui 的防故障机制，防止鼠标移到屏幕边缘报错
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
    
    root = tk.Tk()
    app = GenshinDialogueSkipper(root)
    root.mainloop()