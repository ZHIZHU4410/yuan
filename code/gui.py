import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from presets import PresetManager
from utils import ToolTip
from macro_logic import MacroController, ComboProfile


class GameMacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("我要成为原神高手")
        self.root.geometry("900x700")
        self.root.minsize(900, 700)
        self.root.resizable(True, True)
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TLabel", font=("Microsoft YaHei", 10))

        # 基本功能变量
        self.freq_var = tk.DoubleVar(value=10.0)
        self.hotkey_click = tk.StringVar(value="f6")
        self.speed_move = tk.DoubleVar(value=300.0)
        self.dir_move = tk.StringVar(value="右")
        self.hotkey_move = tk.StringVar(value="f7")
        self.speed_rot = tk.DoubleVar(value=1500.0)
        self.dir_rot = tk.StringVar(value="向右旋转")
        self.hotkey_rot = tk.StringVar(value="f8")

        # 标签
        self.lbl_click = None
        self.lbl_move = None
        self.lbl_rot = None

        # 连招数据
        self.combos = []
        self.combo_tree = None
        self.selected_combo = None

        # 构建 UI
        self.build_ui()

        # 创建控制器并传入 getter/setter
        getters = {
            'freq': lambda: self.freq_var.get(),
            'dir_move': lambda: self.dir_move.get(),
            'speed_move': lambda: self.speed_move.get(),
            'dir_rot': lambda: self.dir_rot.get(),
            'speed_rot': lambda: self.speed_rot.get(),
        }

        def set_label(key, text, color):
            mapping = {
                'click': self.lbl_click,
                'move': self.lbl_move,
                'rotate': self.lbl_rot,
            }
            lbl = mapping.get(key)
            if lbl:
                lbl.config(text=text, foreground=color)

        self.controller = MacroController(getters, set_label)
        # 设置连招状态改变回调，安全刷新列表
        self.controller.set_state_changed_callback(
            lambda profile: self.root.after(0, self.refresh_combo_list)
        )

        # 加载保存的连招配置
        self.load_combos()

        # 注册基础功能热键
        self.update_hotkeys()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        top_bar = ttk.Frame(self.root, padding="10")
        top_bar.pack(fill=tk.X)
        ttk.Label(top_bar, text="我要成为原神高手", font=("Microsoft YaHei", 14, "bold")).pack(side=tk.LEFT)

        notebook = ttk.Notebook(self.root, padding="10")
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 基础功能标签页
        page_click = ttk.Frame(notebook)
        notebook.add(page_click, text="连点")
        self.build_click_page(page_click)

        page_move = ttk.Frame(notebook)
        notebook.add(page_move, text="平移")
        self.build_move_page(page_move)

        page_rotate = ttk.Frame(notebook)
        notebook.add(page_rotate, text="视角")
        self.build_rotate_page(page_rotate)

        # 连招管理标签页
        page_combo = ttk.Frame(notebook)
        notebook.add(page_combo, text="连招管理")
        self.build_combo_manager_page(page_combo)

        # 底部保存按钮
        bottom = ttk.Frame(self.root, padding="10")
        bottom.pack(fill=tk.X)
        self.btn_save = ttk.Button(bottom, text="💾 保存并应用所有热键", command=self.update_hotkeys)
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
        self.lbl_click = ttk.Label(frame, text="● 已停止", foreground="gray")
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
        self.lbl_move = ttk.Label(frame, text="● 已停止", foreground="gray")
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
        self.lbl_rot = ttk.Label(frame, text="● 已停止", foreground="gray")
        self.lbl_rot.grid(row=2, column=0, columnspan=4, pady=15, sticky="we")

    def build_combo_manager_page(self, parent):
        """连招管理页面"""
        main_frame = ttk.Frame(parent, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(toolbar, text="➕ 新建连招", command=self.add_combo).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="✏️ 编辑连招", command=self.edit_combo).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑️ 删除连招", command=self.delete_combo).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄 保存全部", command=self.save_combos).pack(side=tk.LEFT, padx=2)
        
        # 连招列表
        list_frame = ttk.LabelFrame(main_frame, text="连招列表", padding=5)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("热键", "重复次数", "状态", "序列预览")
        self.combo_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        
        self.combo_tree.heading("热键", text="热键")
        self.combo_tree.heading("重复次数", text="重复次数")
        self.combo_tree.heading("状态", text="状态")
        self.combo_tree.heading("序列预览", text="序列预览")
        
        self.combo_tree.column("热键", width=120)
        self.combo_tree.column("重复次数", width=80)
        self.combo_tree.column("状态", width=80)
        self.combo_tree.column("序列预览", width=400)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.combo_tree.yview)
        self.combo_tree.configure(yscrollcommand=scrollbar.set)
        
        self.combo_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定选择事件
        self.combo_tree.bind('<<TreeviewSelect>>', self.on_combo_select)
        
        # 帮助文本（带滚动条，可复制）
        help_frame = ttk.LabelFrame(main_frame, text="帮助（可选中复制）", padding=5)
        help_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))
        
        text_frame = ttk.Frame(help_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.help_text = tk.Text(text_frame, wrap=tk.WORD, height=6, font=("Consolas", 9),
                                 bg="#f0f0f0", relief=tk.FLAT, borderwidth=0)
        scroll_help = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.help_text.yview)
        self.help_text.configure(yscrollcommand=scroll_help.set)
        
        self.help_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_help.pack(side=tk.RIGHT, fill=tk.Y)
        
        help_content = """连招语法说明：
1. 简单格式（分号分隔）：j,0.1,0.2;left_click,0.1,0.3;k,0.05,0.1
   格式：动作,按住时长(秒),间隔(秒)
   鼠标：left_click / right_click / middle_click
   键盘：直接使用按键字符
    
2. 高级花括号格式：{LMB}{WAITMS:200}{RMB}{WAITMS:100}{K}
   支持：LMB/RMB/MMB(按下抬起), LMBD/LMBU(分别按下抬起), WAITMS:毫秒, 单字符按键
   
提示：鼠标左键按下并抬起可用 {LMB}，如需分开控制按下和抬起用 {LMBD}{LMBU}
     文本支持鼠标选择并用 Ctrl+C 复制"""
        
        self.help_text.insert("1.0", help_content)
        self.help_text.configure(state='normal')
        self.help_text.bind("<Key>", lambda e: "break")
        self._add_copy_menu(self.help_text)

    def _add_copy_menu(self, widget):
        """为 Text 组件添加右键复制菜单"""
        def show_menu(event):
            menu = tk.Menu(widget, tearoff=0)
            menu.add_command(label="复制", command=lambda: widget.event_generate("<<Copy>>"))
            menu.post(event.x_root, event.y_root)
        widget.bind("<Button-3>", show_menu)

    def add_combo(self):
        """添加新连招"""
        dialog = ComboEditDialog(self.root, self.controller)
        if dialog.result:
            name, hotkey, sequence, repeat = dialog.result
            # 检查热键是否冲突
            if self.controller.is_hotkey_used(hotkey):
                messagebox.showerror("错误", f"热键 {hotkey} 已被使用")
                return
            profile = ComboProfile(name, hotkey, sequence, repeat)
            self.combos.append(profile)
            self.controller.add_combo(profile)
            self.refresh_combo_list()
            self.update_hotkeys()
            messagebox.showinfo("成功", f"连招 '{name}' 已创建，热键: {hotkey}")

    def edit_combo(self):
        """编辑选中的连招"""
        selected = self.combo_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一个连招")
            return
        
        item = self.combo_tree.item(selected[0])
        profile = item.get('tags', [None])[0]
        if not profile:
            return
        
        dialog = ComboEditDialog(self.root, self.controller, profile)
        if dialog.result:
            name, hotkey, sequence, repeat = dialog.result
            
            # 热键变更检查
            if hotkey != profile.hotkey and self.controller.is_hotkey_used(hotkey):
                messagebox.showerror("错误", f"热键 {hotkey} 已被使用")
                return
            
            # 更新配置
            old_hotkey = profile.hotkey
            profile.name = name
            profile.hotkey = hotkey
            profile.sequence = sequence
            profile.repeat = repeat
            
            # 更新控制器
            self.controller.update_combo_hotkey(profile, old_hotkey)
            
            self.refresh_combo_list()
            self.update_hotkeys()
            messagebox.showinfo("成功", f"连招 '{name}' 已更新")

    def delete_combo(self):
        """删除选中的连招"""
        selected = self.combo_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一个连招")
            return
        
        item = self.combo_tree.item(selected[0])
        profile = item.get('tags', [None])[0]
        if not profile:
            return
        
        if messagebox.askyesno("确认", f"确定要删除连招 '{profile.name}' 吗？"):
            self.controller.remove_combo(profile)
            self.combos.remove(profile)
            self.refresh_combo_list()
            self.update_hotkeys()

    def refresh_combo_list(self):
        """刷新连招列表显示"""
        for item in self.combo_tree.get_children():
            self.combo_tree.delete(item)
        
        for profile in self.combos:
            status = "运行中" if self.controller.get_combo_state(profile) else "● 已停止"
            preview = profile.sequence[:50] + "..." if len(profile.sequence) > 50 else profile.sequence
            self.combo_tree.insert("", tk.END, values=(
                profile.hotkey, profile.repeat, status, preview
            ), tags=(profile,))
        
        # 绑定双击运行/停止
        self.combo_tree.bind('<Double-1>', self.toggle_combo_from_tree)

    def on_combo_select(self, event):
        """选中连招时的处理"""
        selected = self.combo_tree.selection()
        if selected:
            item = self.combo_tree.item(selected[0])
            self.selected_combo = item.get('tags', [None])[0]

    def toggle_combo_from_tree(self, event):
        """双击切换连招运行状态"""
        selected = self.combo_tree.selection()
        if not selected:
            return
        item = self.combo_tree.item(selected[0])
        profile = item.get('tags', [None])[0]
        if profile:
            self.controller.toggle_combo(profile)

    def load_combos(self):
        """加载保存的连招配置"""
        import json
        import os
        
        config_file = "combos.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for combo_data in data:
                        profile = ComboProfile(
                            combo_data['name'],
                            combo_data['hotkey'],
                            combo_data['sequence'],
                            combo_data.get('repeat', 1)
                        )
                        self.combos.append(profile)
                        self.controller.add_combo(profile)
            except Exception as e:
                print(f"加载连招配置失败: {e}")
        
        # 如果没有连招，创建一个默认的
        if not self.combos:
            default_profile = ComboProfile("默认连招", "f9", "j,0.1,0.2;left_click,0.1,0.3;k,0.05,0.1", 1)
            self.combos.append(default_profile)
            self.controller.add_combo(default_profile)
        
        self.refresh_combo_list()

    def save_combos(self):
        """保存连招配置"""
        import json
        
        data = []
        for profile in self.combos:
            data.append({
                'name': profile.name,
                'hotkey': profile.hotkey,
                'sequence': profile.sequence,
                'repeat': profile.repeat
            })
        
        try:
            with open("combos.json", 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("成功", "连招配置已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")

    def parse_hotkey(self, s):
        """解析热键字符串"""
        s = s.lower().strip()
        if s.startswith('f') and s[1:].isdigit():
            return f'<{s}>'
        return s

    def update_hotkeys(self):
        """更新所有热键映射"""
        try:
            # 构建映射字典
            mapping = {
                self.parse_hotkey(self.hotkey_click.get()): self.controller.toggle_click,
                self.parse_hotkey(self.hotkey_move.get()): self.controller.toggle_move,
                self.parse_hotkey(self.hotkey_rot.get()): self.controller.toggle_rotate,
            }
            
            # 添加所有连招的热键
            for profile in self.combos:
                hotkey = self.parse_hotkey(profile.hotkey)
                mapping[hotkey] = lambda p=profile: self.controller.toggle_combo(p)
            
            self.controller.register_hotkeys(mapping)
            self.btn_save.config(text="✅ 热键已生效，可切入游戏使用")
            self.root.after(3000, lambda: self.btn_save.config(text="💾 保存并应用所有热键"))
        except Exception as e:
            messagebox.showerror('错误', f"热键冲突或格式错误: {e}")

    def on_close(self):
        """关闭窗口时的清理"""
        self.save_combos()
        self.controller.stop_all()
        self.root.destroy()


class ComboEditDialog:
    """连招编辑对话框"""
    def __init__(self, parent, controller, profile=None):
        self.parent = parent
        self.controller = controller
        self.profile = profile
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑连招" if profile else "新建连招")
        self.dialog.geometry("600x550")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
        
        if profile:
            self.load_profile()
        
        self.dialog.wait_window()

    def create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 名称
        ttk.Label(main_frame, text="连招名称:").grid(row=0, column=0, sticky="w", pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, padx=10, sticky="w")
        
        # 热键
        ttk.Label(main_frame, text="热键:").grid(row=1, column=0, sticky="w", pady=5)
        self.hotkey_var = tk.StringVar()
        hotkey_entry = ttk.Entry(main_frame, textvariable=self.hotkey_var, width=15)
        hotkey_entry.grid(row=1, column=1, padx=10, sticky="w")
        ToolTip(hotkey_entry, "格式: f9, p, ctrl+shift+p 等")
        
        # 重复次数
        ttk.Label(main_frame, text="重复次数:").grid(row=2, column=0, sticky="w", pady=5)
        self.repeat_var = tk.IntVar(value=1)
        ttk.Spinbox(main_frame, from_=1, to=999, textvariable=self.repeat_var, width=10).grid(row=2, column=1, padx=10, sticky="w")
        
        # 序列内容
        ttk.Label(main_frame, text="连招序列:").grid(row=3, column=0, sticky="nw", pady=5)
        
        seq_frame = ttk.Frame(main_frame)
        seq_frame.grid(row=3, column=1, padx=10, pady=5, sticky="nsew")
        
        self.seq_text = tk.Text(seq_frame, height=12, width=50, font=("Consolas", 10), wrap="word")
        scroll_seq = ttk.Scrollbar(seq_frame, orient="vertical", command=self.seq_text.yview)
        self.seq_text.configure(yscrollcommand=scroll_seq.set)
        
        self.seq_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_seq.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="确定", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # 配置网格权重
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # 帮助文本（带滚动条，可复制）
        help_frame = ttk.LabelFrame(main_frame, text="格式说明（可选中复制）", padding=5)
        help_frame.grid(row=5, column=0, columnspan=2, sticky="we", pady=10)
        
        text_frame = ttk.Frame(help_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.help_text = tk.Text(text_frame, wrap=tk.WORD, height=5, font=("Consolas", 9),
                                 bg="#f0f0f0", relief=tk.FLAT, borderwidth=0)
        scroll_help = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.help_text.yview)
        self.help_text.configure(yscrollcommand=scroll_help.set)
        
        self.help_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_help.pack(side=tk.RIGHT, fill=tk.Y)
        
        help_content = """简单格式示例：
j,0.1,0.2;left_click,0.1,0.3;k,0.05,0.1
说明：j键按住0.1秒间隔0.2秒，鼠标左键按住0.1秒间隔0.3秒...

高级格式示例：
{LMB}{WAITMS:200}{LMBU}{WAITMS:100}{K}
说明：按下左键，等待200毫秒，抬起左键，等待100毫秒，按下K键并抬起

提示：鼠标左键按下并抬起可用 {LMB}，如需分开控制按下和抬起用 {LMBD}{LMBU}
     文本支持鼠标选择并用 Ctrl+C 复制"""
        
        self.help_text.insert("1.0", help_content)
        self.help_text.configure(state='normal')
        self.help_text.bind("<Key>", lambda e: "break")
        self._add_copy_menu(self.help_text)

    def _add_copy_menu(self, widget):
        """为 Text 组件添加右键复制菜单"""
        def show_menu(event):
            menu = tk.Menu(widget, tearoff=0)
            menu.add_command(label="复制", command=lambda: widget.event_generate("<<Copy>>"))
            menu.post(event.x_root, event.y_root)
        widget.bind("<Button-3>", show_menu)

    def load_profile(self):
        """加载已有连招配置"""
        self.name_var.set(self.profile.name)
        self.hotkey_var.set(self.profile.hotkey)
        self.repeat_var.set(self.profile.repeat)
        self.seq_text.insert("1.0", self.profile.sequence)

    def on_ok(self):
        """确认按钮回调"""
        name = self.name_var.get().strip()
        hotkey = self.hotkey_var.get().strip().lower()
        sequence = self.seq_text.get("1.0", "end-1c").strip()
        repeat = self.repeat_var.get()
        
        if not name:
            messagebox.showwarning("警告", "请输入连招名称")
            return
        if not hotkey:
            messagebox.showwarning("警告", "请输入热键")
            return
        if not sequence:
            messagebox.showwarning("警告", "请输入连招序列")
            return
        if repeat < 1:
            repeat = 1
        
        self.result = (name, hotkey, sequence, repeat)
        self.dialog.destroy()