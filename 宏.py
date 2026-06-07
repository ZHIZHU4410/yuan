import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading, time, math, ctypes, json, os
import pyautogui
from pynput import keyboard, mouse

# ================= 核心配置 =================
SLEEP_INTERVAL = 0.005
MOUSEEVENTF_MOVE = 0x0001

def game_compatible_move(dx, dy):
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, int(dx), int(dy), 0, 0)

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind('<Enter>', self.show)
        widget.bind('<Leave>', self.hide)

    def show(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Microsoft YaHei", 9))
        label.pack(ipadx=5, ipady=3)

    def hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class GameMacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("我要成为原神高手")
        self.root.geometry("520x750") # 稍微调高了一点以适应新UI
        self.root.resizable(False, False)
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TLabel", font=("Microsoft YaHei", 10))
        self.style.configure("TLabelframe.Label", font=("Microsoft YaHei", 11, "bold"), foreground="#2c3e50")
        self.style.configure("TButton", font=("Microsoft YaHei", 10), padding=5)
        self.style.configure("TEntry", font=("Consolas", 10))
        self.style.configure("TCombobox", font=("Microsoft YaHei", 10))
        self.style.configure("Status.TLabel", font=("Microsoft YaHei", 10, "bold"), anchor="center")
        self.style.configure("Title.TLabel", font=("Microsoft YaHei", 12, "bold"), foreground="#2980b9")

        self.running_states = {'click': False, 'move': False, 'rotate': False, 'combo': False}
        self.events = {
            'click': threading.Event(),
            'move': threading.Event(),
            'rotate': threading.Event(),
            'combo': threading.Event()
        }
        self.hotkey_listener = None
        self.accum_x = self.accum_y = self.rot_accum = 0.0

        # 初始化预设数据
        self.preset_file = "presets.json"
        self.presets = self.load_presets()
        self.current_preset = tk.StringVar()

        # UI 变量
        self.freq_var = tk.DoubleVar(value=10.0)
        self.hotkey_click = tk.StringVar(value="f6")
        self.speed_move = tk.DoubleVar(value=300.0)
        self.dir_move = tk.StringVar(value="右")
        self.hotkey_move = tk.StringVar(value="f7")
        self.speed_rot = tk.DoubleVar(value=1500.0)
        self.dir_rot = tk.StringVar(value="向右旋转")
        self.hotkey_rot = tk.StringVar(value="f8")
        self.combo_sequence = tk.StringVar(value="j,0.1,0.2;left_click,0.1,0.3;k,0.05,0.1")
        self.combo_repeat = tk.IntVar(value=1)
        self.hotkey_combo = tk.StringVar(value="f9")

        # 鼠标动作映射
        self.mouse_button_map = {
            'left_click': mouse.Button.left,
            'right_click': mouse.Button.right,
            'middle_click': mouse.Button.middle,
        }

        self.build_ui()
        self.update_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ================= 预设管理逻辑 =================
    def load_presets(self):
        if os.path.exists(self.preset_file):
            try:
                with open(self.preset_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"默认连招": "j,0.1,0.2;left_click,0.1,0.3;k,0.05,0.1"}

    def _save_presets_to_file(self):
        with open(self.preset_file, 'w', encoding='utf-8') as f:
            json.dump(self.presets, f, ensure_ascii=False, indent=2)

    def on_preset_selected(self, event=None):
        name = self.current_preset.get()
        if name in self.presets:
            self.seq_text.delete("1.0", tk.END)
            self.seq_text.insert("1.0", self.presets[name])

    def save_preset(self):
        name = simpledialog.askstring("保存预设", "请输入预设名称：", parent=self.root)
        if name:
            name = name.strip()
            if not name: return
            self.presets[name] = self.seq_text.get("1.0", "end-1c").strip()
            self._save_presets_to_file()
            self.preset_combo['values'] = list(self.presets.keys())
            self.current_preset.set(name)
            messagebox.showinfo("成功", f"预设 '{name}' 已保存！")

    def delete_preset(self):
        name = self.current_preset.get()
        if not name:
            messagebox.showwarning("警告", "请先选择一个要删除的预设！")
            return
        if messagebox.askyesno("确认", f"确定要删除预设 '{name}' 吗？"):
            if name in self.presets:
                del self.presets[name]
                self._save_presets_to_file()
                self.preset_combo['values'] = list(self.presets.keys())
                self.current_preset.set('')
                self.seq_text.delete("1.0", tk.END)
                messagebox.showinfo("成功", "预设已删除！")

    def build_ui(self):
        top_bar = ttk.Frame(self.root, padding="10")
        top_bar.pack(fill=tk.X)
        ttk.Label(top_bar, text="我要成为原神高手", style="Title.TLabel").pack(side=tk.LEFT)

        notebook = ttk.Notebook(self.root, padding="10")
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        page_click = ttk.Frame(notebook)
        notebook.add(page_click, text="连点")
        self.build_click_page(page_click)

        page_move = ttk.Frame(notebook)
        notebook.add(page_move, text="平移")
        self.build_move_page(page_move)

        page_rotate = ttk.Frame(notebook)
        notebook.add(page_rotate, text="视角")
        self.build_rotate_page(page_rotate)

        page_combo = ttk.Frame(notebook)
        notebook.add(page_combo, text="连招")
        self.build_combo_page(page_combo)

        bottom = ttk.Frame(self.root, padding="10")
        bottom.pack(fill=tk.X)
        self.btn_save = ttk.Button(bottom, text="保存并应用所有热键", command=self.update_hotkeys)
        self.btn_save.pack(fill=tk.X, ipady=8)

    def build_click_page(self, parent):
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="频率 (次/秒):").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.freq_var, width=10).grid(row=0, column=1, padx=10, sticky="w")
        ttk.Label(frame, text="快捷键:").grid(row=1, column=0, sticky="w", pady=5)
        hotkey_entry = ttk.Entry(frame, textvariable=self.hotkey_click, width=10)
        hotkey_entry.grid(row=1, column=1, padx=10, sticky="w")
        ToolTip(hotkey_entry, "格式: f6 或 ctrl+shift+a\n修改后需点下方'保存'生效")
        self.lbl_click = ttk.Label(frame, text="● 已停止", style="Status.TLabel", foreground="gray")
        self.lbl_click.grid(row=2, column=0, columnspan=2, pady=15, sticky="we")

    def build_move_page(self, parent):
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="移动速度:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.speed_move, width=10).grid(row=0, column=1, padx=10)
        ttk.Label(frame, text="移动方向:").grid(row=0, column=2, sticky="e", padx=5)
        dirs = ["上","下","左","右","左上","右上","左下","右下"]
        ttk.Combobox(frame, textvariable=self.dir_move, values=dirs, width=8, state="readonly").grid(row=0, column=3)
        ttk.Label(frame, text="快捷键:").grid(row=1, column=0, sticky="w", pady=5)
        hotkey_entry = ttk.Entry(frame, textvariable=self.hotkey_move, width=10)
        hotkey_entry.grid(row=1, column=1, padx=10)
        ToolTip(hotkey_entry, "格式: f7 或 ctrl+shift+b")
        self.lbl_move = ttk.Label(frame, text="● 已停止", style="Status.TLabel", foreground="gray")
        self.lbl_move.grid(row=2, column=0, columnspan=4, pady=15, sticky="we")

    def build_rotate_page(self, parent):
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="旋转速度:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.speed_rot, width=10).grid(row=0, column=1, padx=10)
        ttk.Label(frame, text="旋转方向:").grid(row=0, column=2, sticky="e", padx=5)
        dirs = ["向左旋转", "向右旋转"]
        ttk.Combobox(frame, textvariable=self.dir_rot, values=dirs, width=10, state="readonly").grid(row=0, column=3)
        ttk.Label(frame, text="快捷键:").grid(row=1, column=0, sticky="w", pady=5)
        hotkey_entry = ttk.Entry(frame, textvariable=self.hotkey_rot, width=10)
        hotkey_entry.grid(row=1, column=1, padx=10)
        ToolTip(hotkey_entry, "格式: f8 或 ctrl+alt+r")
        self.lbl_rot = ttk.Label(frame, text="● 已停止", style="Status.TLabel", foreground="gray")
        self.lbl_rot.grid(row=2, column=0, columnspan=4, pady=15, sticky="we")

    def build_combo_page(self, parent):
        frame = ttk.Frame(parent, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # ---------------- 预设功能区 ----------------
        preset_frame = ttk.Frame(frame)
        preset_frame.grid(row=0, column=0, columnspan=3, sticky="we", pady=(0, 10))

        ttk.Label(preset_frame, text="预设配置:").pack(side=tk.LEFT)
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.current_preset, state="readonly", width=12)
        self.preset_combo['values'] = list(self.presets.keys())
        self.preset_combo.pack(side=tk.LEFT, padx=5)
        self.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_selected)

        ttk.Button(preset_frame, text="💾 保存当前", command=self.save_preset).pack(side=tk.LEFT, padx=(5, 2))
        ttk.Button(preset_frame, text="🗑️ 删除", command=self.delete_preset).pack(side=tk.LEFT)
        # --------------------------------------------

        # 序列配置：多行 Text
        ttk.Label(frame, text="序列内容:").grid(row=1, column=0, sticky="nw", pady=5)
        self.seq_text = tk.Text(frame, height=4, width=40, font=("Consolas", 10),
                                wrap="word", undo=True)
        self.seq_text.grid(row=1, column=1, padx=10, sticky="ew")
        
        # 插入默认内容（优先加载下拉框第一个预设）
        default_preset_name = list(self.presets.keys())[0] if self.presets else None
        if default_preset_name:
            self.current_preset.set(default_preset_name)
            self.seq_text.insert("1.0", self.presets[default_preset_name])
        else:
            self.seq_text.insert("1.0", "j,0.1,0.2;left_click,0.1,0.3;k,0.05,0.1")
            
        # 滚动条
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.seq_text.yview)
        scroll.grid(row=1, column=2, sticky="ns")
        self.seq_text.configure(yscrollcommand=scroll.set)

        ToolTip(self.seq_text, "每个动作用分号分隔，格式: 动作,按住时长,间隔\n"
                            "键盘：a,0.1,0.2\n"
                            "鼠标：left_click,0.1,0.2  / right_click,0.1,0.2  / middle_click,0.1,0.2\n"
                            "纯延迟：wait,0,0.5")

        # 循环次数
        ttk.Label(frame, text="循环次数:").grid(row=2, column=0, sticky="w", pady=5)
        repeat_entry = ttk.Entry(frame, textvariable=self.combo_repeat, width=8)
        repeat_entry.grid(row=2, column=1, padx=10, sticky="w")
        ToolTip(repeat_entry, "执行多少轮完整序列，默认为1")

        # 快捷键
        ttk.Label(frame, text="快捷键:").grid(row=3, column=0, sticky="w", pady=5)
        hotkey_entry = ttk.Entry(frame, textvariable=self.hotkey_combo, width=10)
        hotkey_entry.grid(row=3, column=1, padx=10, sticky="w")
        ToolTip(hotkey_entry, "格式: f9")

        # 状态
        self.lbl_combo = ttk.Label(frame, text="● 已停止", style="Status.TLabel", foreground="gray")
        self.lbl_combo.grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky="we")

        # 说明文本（只读，可复制）
        help_text = "格式：动作,按住时长,间隔  (分号分隔)\n鼠标: left_click/right_click/middle_click\n纯延迟: wait,0,秒数\n或者使用花括号新语法：{LMBD}{WAITMS:200}{LMBU}"
        self.help_text_widget = tk.Text(frame, height=4, width=60, font=("Consolas", 10),
                                        bg="#f0f0f0", relief="flat", borderwidth=1,
                                        wrap="word", state='normal')
        self.help_text_widget.insert("1.0", help_text)
        self.help_text_widget.config(state='disabled')
        self.help_text_widget.grid(row=5, column=0, columnspan=3, pady=5, sticky='we')

        frame.columnconfigure(1, weight=1)

    # ================= 热键逻辑 =================
    def parse_hotkey(self, s):
        s = s.lower().strip()
        if s.startswith('f') and s[1:].isdigit(): return f'<{s}>'
        return s

    def update_hotkeys(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        try:
            mapping = {
                self.parse_hotkey(self.hotkey_click.get()): self.toggle_click,
                self.parse_hotkey(self.hotkey_move.get()): self.toggle_move,
                self.parse_hotkey(self.hotkey_rot.get()): self.toggle_rotate,
                self.parse_hotkey(self.hotkey_combo.get()): self.toggle_combo
            }
            self.hotkey_listener = keyboard.GlobalHotKeys(mapping)
            self.hotkey_listener.start()
            self.btn_save.config(text="✅ 热键已生效，可切入游戏使用")
            self.root.after(3000, lambda: self.btn_save.config(text="💾 保存并应用所有热键"))
        except Exception as e:
            messagebox.showerror("错误", f"热键冲突或格式错误: {e}")

    # ================= 功能逻辑 =================
    def toggle_click(self):
        state = not self.running_states['click']
        self.running_states['click'] = state
        if state:
            self.events['click'].clear()
            self.lbl_click.config(text="🟢 连点运行中", foreground="green")
            threading.Thread(target=self.click_loop, daemon=True).start()
        else:
            self.events['click'].set()
            self.lbl_click.config(text="● 已停止", foreground="gray")

    def click_loop(self):
        while not self.events['click'].is_set() and self.running_states['click']:
            pyautogui.click(_pause=False)
            try: time.sleep(1.0 / self.freq_var.get())
            except: break

    def toggle_move(self):
        state = not self.running_states['move']
        self.running_states['move'] = state
        if state:
            self.events['move'].clear()
            self.accum_x = self.accum_y = 0.0
            self.lbl_move.config(text="🟢 平移移动中", foreground="green")
            threading.Thread(target=self.move_loop, daemon=True).start()
        else:
            self.events['move'].set()
            self.lbl_move.config(text="● 已停止", foreground="gray")

    def move_loop(self):
        dir_map = {"上":(0,-1),"下":(0,1),"左":(-1,0),"右":(1,0),
                   "左上":(-1,-1),"右上":(1,-1),"左下":(-1,1),"右下":(1,1)}
        last_time = time.perf_counter()
        while not self.events['move'].is_set() and self.running_states['move']:
            dt = time.perf_counter() - last_time
            last_time = time.perf_counter()
            try:
                dx, dy = dir_map.get(self.dir_move.get(), (0,0))
                mag = math.hypot(dx, dy)
                if mag > 0: dx, dy = dx/mag, dy/mag
                self.accum_x += self.speed_move.get() * dt * dx
                self.accum_y += self.speed_move.get() * dt * dy
                ix, iy = int(self.accum_x), int(self.accum_y)
                if ix or iy:
                    game_compatible_move(ix, iy)
                    self.accum_x -= ix
                    self.accum_y -= iy
            except: break
            time.sleep(SLEEP_INTERVAL)

    def toggle_rotate(self):
        state = not self.running_states['rotate']
        self.running_states['rotate'] = state
        if state:
            self.events['rotate'].clear()
            self.rot_accum = 0.0
            self.lbl_rot.config(text="🟢 视角旋转中", foreground="green")
            threading.Thread(target=self.rotate_loop, daemon=True).start()
        else:
            self.events['rotate'].set()
            self.lbl_rot.config(text="● 已停止", foreground="gray")

    def rotate_loop(self):
        last_time = time.perf_counter()
        while not self.events['rotate'].is_set() and self.running_states['rotate']:
            curr_time = time.perf_counter()
            dt = curr_time - last_time
            last_time = curr_time
            try:
                speed = self.speed_rot.get()
                direction = -1 if "左" in self.dir_rot.get() else 1
                step_x = speed * dt * direction
                self.rot_accum += step_x
                int_x = int(self.rot_accum)
                if int_x:
                    game_compatible_move(int_x, 0)
                    self.rot_accum -= int_x
            except: break
            time.sleep(SLEEP_INTERVAL)

    # ================= 连招逻辑（支持鼠标点击和延迟） =================
    def toggle_combo(self):
        state = not self.running_states['combo']
        self.running_states['combo'] = state
        if state:
            self.events['combo'].clear()
            self.lbl_combo.config(text="🟢 连招循环中", foreground="green")
            threading.Thread(target=self.combo_loop, daemon=True).start()
        else:
            self.events['combo'].set()
            self.lbl_combo.config(text="● 已停止", foreground="gray")

    def parse_raw_macro(self, text):
        steps = []
        i = 0
        n = len(text)
        # 鼠标按钮映射
        mouse_buttons = {
            'LMB': 'left',
            'RMB': 'right',
            'MMB': 'middle'
        }
        while i < n:
            if text[i] == '{':
                j = text.find('}', i)
                if j == -1:
                    break
                cmd = text[i+1:j].strip()
                i = j + 1

                # 解析命令
                if cmd.startswith('WAITMS:'):
                    ms = int(cmd.split(':')[1])
                    steps.append(('wait', None, ms / 1000.0))
                elif cmd.startswith('HOLDMS:'):
                    parts = cmd.split(':')
                    ms = int(parts[1])
                    # 跳过空格、换行等
                    while i < n and text[i] in (' ', '\t', '\r', '\n'):
                        i += 1
                    if i < n and text[i] != '{':
                        key = text[i]
                        i += 1
                    else:
                        key = None
                    if key:
                        steps.append(('key_down', key, 0))
                        steps.append(('wait', None, ms / 1000.0))
                        steps.append(('key_up', key, 0))
                elif cmd in mouse_buttons:
                    btn = mouse_buttons[cmd]
                    steps.append(('mouse_down', btn, 0))
                    steps.append(('mouse_up', btn, 0))
                elif cmd == 'LMBD':
                    steps.append(('mouse_down', 'left', 0))
                elif cmd == 'LMBU':
                    steps.append(('mouse_up', 'left', 0))
                elif cmd == 'RMBD':
                    steps.append(('mouse_down', 'right', 0))
                elif cmd == 'RMBU':
                    steps.append(('mouse_up', 'right', 0))
                elif cmd == 'MMBD':
                    steps.append(('mouse_down', 'middle', 0))
                elif cmd == 'MMBU':
                    steps.append(('mouse_up', 'middle', 0))
                elif len(cmd) == 1:
                    steps.append(('key_down', cmd, 0))
                    steps.append(('key_up', cmd, 0))
                else:
                    pass
            elif text[i] in ('\r', '\n', '\t', ' '):
                i += 1
            else:
                i += 1
        return steps
    
    def combo_loop(self):
        raw_seq = self.seq_text.get("1.0", "end-1c").strip()
        
        # ---- 统一解析为内部步骤格式： (动作类型, 参数, 等待秒数) ----
        if raw_seq.startswith('{'):
            steps = self.parse_raw_macro(raw_seq)
            if not steps:
                self.lbl_combo.config(text="⚠️ 宏解析失败", foreground="red")
                self.running_states['combo'] = False
                return
        else:
            items = raw_seq.split(';')
            steps = []
            for item in items:
                item = item.strip()
                if not item:
                    continue
                parts = item.split(',')
                if len(parts) != 3:
                    continue
                action = parts[0].strip().lower()
                try:
                    hold = float(parts[1])
                    interval = float(parts[2])
                except ValueError:
                    continue

                if action in ('wait', 'delay'):
                    steps.append(('wait', None, interval))
                else:
                    btn_name = self.mouse_button_map.get(action)
                    if btn_name is not None:
                        base_name = action.split('_')[0]
                        steps.append(('mouse_down', base_name, 0))
                        steps.append(('wait', None, hold))
                        steps.append(('mouse_up', base_name, 0))
                        steps.append(('wait', None, interval))
                    else:
                        steps.append(('key_down', action, 0))
                        steps.append(('wait', None, hold))
                        steps.append(('key_up', action, 0))
                        steps.append(('wait', None, interval))

            if not steps:
                self.lbl_combo.config(text="⚠️ 序列为空", foreground="red")
                self.running_states['combo'] = False
                return

        repeat_count = self.combo_repeat.get()
        if repeat_count <= 0:
            repeat_count = 1
            self.combo_repeat.set(1)

        kb_controller = keyboard.Controller()
        ms_controller = mouse.Controller()

        mouse_btn_map = {
            'left': mouse.Button.left,
            'right': mouse.Button.right,
            'middle': mouse.Button.middle,
        }

        # ===== 统一执行新格式步骤 =====
        for _ in range(repeat_count):
            if self.events['combo'].is_set() or not self.running_states['combo']:
                break
            for typ, param, wait in steps:
                if self.events['combo'].is_set() or not self.running_states['combo']:
                    break
                try:
                    if typ == 'key_down':
                        kb_controller.press(param)
                    elif typ == 'key_up':
                        kb_controller.release(param)
                    elif typ == 'mouse_down':
                        btn = mouse_btn_map.get(param)
                        if btn:
                            ms_controller.press(btn)
                    elif typ == 'mouse_up':
                        btn = mouse_btn_map.get(param)
                        if btn:
                            ms_controller.release(btn)
                    elif typ == 'wait':
                        pass
                    if wait > 0:
                        time.sleep(wait)
                except Exception:
                    pass

        self.running_states['combo'] = False
        self.events['combo'].set()
        self.lbl_combo.config(text="● 已停止", foreground="gray")

    
    def on_close(self):
        for k in self.running_states:
            self.running_states[k] = False
            self.events[k].set()
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
    root = tk.Tk()
    app = GameMacroApp(root)
    root.mainloop()