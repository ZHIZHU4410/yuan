"""
键盘宏录制工具 - GUI 版
用法：直接运行此脚本，或打包成 exe。
功能：按 F9 开始录制，按 F10 停止录制，生成的宏代码显示在文本框，可复制并保存到文件。
支持录制键盘按键和鼠标点击（左键、右键、中键），生成兼容 macro_logic 的花括号格式。
"""

import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from pynput import keyboard, mouse

# 配置
RECORD_START_HOTKEY = '<f9>'
RECORD_STOP_HOTKEY = '<f10>'
MERGE_THRESHOLD_MS = 30          # 按下和抬起间隔小于此值（毫秒）时合并为单击

class MacroRecorderGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("键盘宏录制工具")
        self.root.geometry("700x650")
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 状态变量
        self.recording = False
        self.events = []           # 存储 (event_type, key_name, timestamp)
        self.key_state = {}        # 用于检测按键持续时间（保留以备未来使用）

        # 热键键值（用于过滤）
        self.start_hotkey_key = keyboard.Key.f9
        self.stop_hotkey_key = keyboard.Key.f10

        # 监听器
        self.keyboard_listener = None
        self.mouse_listener = None
        self.hotkey_listener = None

        # 构建界面
        self.build_ui()

        # 启动键盘和鼠标监听（全局）
        self.start_keyboard_listener()
        self.start_mouse_listener()

        # 注册全局热键（使用 pynput 的 GlobalHotKeys，会在后台线程运行）
        self.register_hotkeys()

        self.root.mainloop()

    def build_ui(self):
        """构建界面控件"""
        # 顶部控制栏
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(fill=tk.X)

        self.btn_start = ttk.Button(control_frame, text="开始录制 (F9)", command=self.start_recording)
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_stop = ttk.Button(control_frame, text="停止录制 (F10)", command=self.stop_recording, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(control_frame, text="状态：未录制", foreground="gray")
        self.status_label.pack(side=tk.LEFT, padx=20)

        # 宏代码显示区域
        display_frame = ttk.LabelFrame(self.root, text="生成的宏代码", padding=10)
        display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.macro_text = scrolledtext.ScrolledText(display_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.macro_text.pack(fill=tk.BOTH, expand=True)

        # 底部按钮栏
        bottom_frame = ttk.Frame(self.root, padding=10)
        bottom_frame.pack(fill=tk.X)

        ttk.Button(bottom_frame, text="复制到剪贴板", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="保存到文件", command=self.save_to_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="清空显示", command=self.clear_display).pack(side=tk.LEFT, padx=5)

        # 帮助信息
        help_text = "使用说明：\n• 按 F9 开始录制，按 F10 停止录制。\n• 录制时会记录键盘按键和鼠标点击（F9/F10 不会被记录）。\n• 按下和抬起间隔小于 30ms 时会合并为单击（{K} 或 {LMB} 等）。\n• 生成的宏代码可直接复制到主程序的连招编辑框中使用。"
        help_label = ttk.Label(bottom_frame, text=help_text, foreground="gray", justify=tk.LEFT)
        help_label.pack(side=tk.RIGHT, padx=10)

    def start_keyboard_listener(self):
        """启动全局键盘监听器（用于记录按键事件）"""
        def on_press(key):
            # 过滤掉 F9/F10
            if key == self.start_hotkey_key or key == self.stop_hotkey_key:
                return
            if not self.recording:
                return

            key_name = self.get_key_name(key)
            if key_name is None:
                return

            now = time.perf_counter()
            self.events.append(('press', key_name, now))
            self.key_state[key_name] = now

        def on_release(key):
            if key == self.start_hotkey_key or key == self.stop_hotkey_key:
                return
            if not self.recording:
                return

            key_name = self.get_key_name(key)
            if key_name is None:
                return

            now = time.perf_counter()
            self.events.append(('release', key_name, now))
            if key_name in self.key_state:
                del self.key_state[key_name]

        self.keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.keyboard_listener.start()

    def start_mouse_listener(self):
        """启动全局鼠标监听器（用于记录鼠标点击事件）"""
        def on_click(x, y, button, pressed):
            if not self.recording:
                return

            # 映射鼠标按键名称
            button_map = {
                mouse.Button.left: "LMB",
                mouse.Button.right: "RMB",
                mouse.Button.middle: "MMB",
            }
            if button not in button_map:
                return  # 忽略其他按键（如侧键）

            key_name = button_map[button]
            event_type = 'press' if pressed else 'release'
            now = time.perf_counter()
            self.events.append((event_type, key_name, now))

            if pressed:
                self.key_state[key_name] = now
            else:
                if key_name in self.key_state:
                    del self.key_state[key_name]

        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()

    def register_hotkeys(self):
        """注册全局热键 F9/F10（用于控制录制开始/停止）"""
        def start_callback():
            # 在 GUI 线程中调用
            self.root.after(0, self.start_recording)

        def stop_callback():
            self.root.after(0, self.stop_recording)

        hotkey_mapping = {
            RECORD_START_HOTKEY: start_callback,
            RECORD_STOP_HOTKEY: stop_callback,
        }
        # 启动热键监听器（在后台线程）
        self.hotkey_listener = keyboard.GlobalHotKeys(hotkey_mapping)
        self.hotkey_listener.start()

    def get_key_name(self, key):
        """将 pynput 的 key 对象转换为可读字符串"""
        try:
            return key.char
        except AttributeError:
            key_map = {
                keyboard.Key.space: "SPACE",
                keyboard.Key.enter: "ENTER",
                keyboard.Key.shift: "SHIFT",
                keyboard.Key.shift_l: "LSHIFT",
                keyboard.Key.shift_r: "RSHIFT",
                keyboard.Key.ctrl: "CTRL",
                keyboard.Key.ctrl_l: "LCTRL",
                keyboard.Key.ctrl_r: "RCTRL",
                keyboard.Key.alt: "ALT",
                keyboard.Key.alt_l: "LALT",
                keyboard.Key.alt_r: "RALT",
                keyboard.Key.cmd: "WIN",
                keyboard.Key.backspace: "BACKSPACE",
                keyboard.Key.tab: "TAB",
                keyboard.Key.caps_lock: "CAPSLOCK",
                keyboard.Key.delete: "DELETE",
                keyboard.Key.home: "HOME",
                keyboard.Key.end: "END",
                keyboard.Key.page_up: "PAGEUP",
                keyboard.Key.page_down: "PAGEDOWN",
                keyboard.Key.up: "UP",
                keyboard.Key.down: "DOWN",
                keyboard.Key.left: "LEFT",
                keyboard.Key.right: "RIGHT",
                keyboard.Key.f1: "F1",
                keyboard.Key.f2: "F2",
                keyboard.Key.f3: "F3",
                keyboard.Key.f4: "F4",
                keyboard.Key.f5: "F5",
                keyboard.Key.f6: "F6",
                keyboard.Key.f7: "F7",
                keyboard.Key.f8: "F8",
                keyboard.Key.f9: "F9",
                keyboard.Key.f10: "F10",
                keyboard.Key.f11: "F11",
                keyboard.Key.f12: "F12",
            }
            return key_map.get(key, str(key).replace("Key.", ""))

    def start_recording(self):
        """开始录制"""
        if self.recording:
            return
        self.events = []
        self.key_state = {}
        self.recording = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_label.config(text="状态：录制中...", foreground="green")
        # 清空之前的显示
        self.clear_display()

    def stop_recording(self):
        """停止录制并生成宏"""
        if not self.recording:
            return
        self.recording = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_label.config(text="状态：已停止", foreground="gray")

        if not self.events:
            messagebox.showinfo("提示", "未录制到任何按键或鼠标点击，宏代码为空。")
            return

        macro = self.generate_macro()
        self.macro_text.delete(1.0, tk.END)
        self.macro_text.insert(tk.END, macro)

    def generate_macro(self):
        """根据事件列表生成花括号宏代码（兼容键盘和鼠标）"""
        if not self.events:
            return ""

        # 转换为带时间差的序列
        sequence = []
        last_time = self.events[0][2]
        for typ, key, t in self.events:
            delta = (t - last_time) * 1000
            if delta > 0:
                sequence.append(('wait', int(round(delta))))
            sequence.append((typ, key))
            last_time = t

        # 合并相近的 press 和 release（单击）
        merged = []
        i = 0
        n = len(sequence)
        while i < n:
            elem = sequence[i]
            if elem[0] == 'wait':
                merged.append(elem)
                i += 1
                continue

            typ, key = elem
            if typ == 'press' and i + 1 < n:
                next_elem = sequence[i+1]
                # 查找对应的 release（跳过中间的 wait）
                idx = i+1
                total_wait = 0
                while idx < n and sequence[idx][0] == 'wait':
                    total_wait += sequence[idx][1]
                    idx += 1
                if idx < n and sequence[idx][0] == 'release' and sequence[idx][1] == key:
                    if total_wait <= MERGE_THRESHOLD_MS:
                        merged.append(('click', key))
                        i = idx + 1
                        continue
            merged.append(elem)
            i += 1

        # 转换为花括号字符串
        output_parts = []
        for item in merged:
            if item[0] == 'wait':
                output_parts.append(f"{{WAITMS:{item[1]}}}")
            elif item[0] == 'click':
                output_parts.append(f"{{{item[1]}}}")
            elif item[0] == 'press':
                # 鼠标按键输出 LMB/RMB/MMB 加上 D 后缀
                output_parts.append(f"{{{item[1]}D}}")
            elif item[0] == 'release':
                # 鼠标按键输出 LMB/RMB/MMB 加上 U 后缀
                output_parts.append(f"{{{item[1]}U}}")
        return ''.join(output_parts)

    def copy_to_clipboard(self):
        """复制宏代码到剪贴板"""
        code = self.macro_text.get(1.0, tk.END).strip()
        if not code:
            messagebox.showwarning("警告", "没有可复制的宏代码。")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        messagebox.showinfo("成功", "宏代码已复制到剪贴板。")

    def save_to_file(self):
        """保存宏代码到文件"""
        code = self.macro_text.get(1.0, tk.END).strip()
        if not code:
            messagebox.showwarning("警告", "没有可保存的宏代码。")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile="macro_output.txt"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(code)
                messagebox.showinfo("成功", f"宏代码已保存到：{file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败：{e}")

    def clear_display(self):
        """清空显示区域"""
        self.macro_text.delete(1.0, tk.END)

    def on_close(self):
        """关闭窗口时清理监听器"""
        if self.keyboard_listener and self.keyboard_listener.running:
            self.keyboard_listener.stop()
        if self.mouse_listener and self.mouse_listener.running:
            self.mouse_listener.stop()
        if self.hotkey_listener and self.hotkey_listener.running:
            self.hotkey_listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    app = MacroRecorderGUI()