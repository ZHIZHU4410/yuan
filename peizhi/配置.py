import tkinter as tk
from tkinter import ttk, messagebox
import os
from typing import Dict, List, Tuple, Union

# ===================== 配置解析器 =====================
class ConfigParser:
    KNOWN_DICTS = {
        'BilibiliCode', 'SerialVerify', 'LikeMapping',
        'DanmuMapping', 'DanmuLevel', 'GiftMapping',
        'SkinIds', 'MeleeWeapons',
        'TeleportConfig', 'GameParams'
    }
    KNOWN_LISTS = {
        'dianzan', 'enter', 'MobIds', 'EasyMobIds',
        'ChestMonsters', 'BagItem', 'Consumable', 'PreciousLoot'
    }
    # 需要从旧列表格式迁移为带序号字典的 section
    NUMBERED_DICTS = {'SkinIds', 'MeleeWeapons'}

    @staticmethod
    def parse(filepath: str) -> Dict[str, Tuple[str, Union[Dict, List]]]:
        if not os.path.exists(filepath):
            return {}

        sections = {}
        current_section = None
        current_type = None
        current_data = None

        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                stripped = line.strip()
                if not stripped or stripped.startswith('//') or stripped.startswith('#'):
                    continue

                if stripped.startswith('[') and stripped.endswith(']'):
                    if current_section is not None:
                        sections[current_section] = (current_type, current_data)
                    current_section = stripped[1:-1].strip()
                    if current_section in ConfigParser.KNOWN_DICTS:
                        current_type = 'dict'
                        current_data = {}
                    elif current_section in ConfigParser.KNOWN_LISTS:
                        current_type = 'list'
                        current_data = []
                    else:
                        current_type = None
                        current_data = None
                    continue

                if current_section is None:
                    continue

                if current_type == 'dict' or (current_type is None and '=' in line):
                    if current_type is None:
                        current_type = 'dict'
                        current_data = {}

                    if '=' in line:
                        key, value = line.split('=', 1)
                        current_data[key.strip()] = value.strip()
                    else:
                        current_data[stripped] = ""
                else:
                    if current_type is None:
                        current_type = 'list'
                        current_data = []
                    current_data.append(stripped)

        if current_section is not None:
            sections[current_section] = (current_type, current_data)

        # 迁移：将旧列表格式的 SkinIds/MeleeWeapons 转为带序号字典（序号从0开始）
        for sec in ConfigParser.NUMBERED_DICTS:
            if sec in sections:
                typ, data = sections[sec]
                if typ == 'list':
                    new_data = {str(i): v for i, v in enumerate(data)}
                    sections[sec] = ('dict', new_data)
                elif typ == 'dict':
                    keys_are_names = all(
                        v == '' and not k.strip().isdigit()
                        for k, v in data.items()
                    )
                    if keys_are_names:
                        new_data = {str(i): k for i, k in enumerate(data.keys())}
                        sections[sec] = ('dict', new_data)

        return sections

    @staticmethod
    def save(filepath: str, sections: Dict[str, Tuple[str, Union[Dict, List]]]) -> None:
        # 自定义保存顺序：基础设置放到最后
        # 基础设置包含：SerialVerify, enter, TeleportConfig, （可自行扩展）
        base_sections = {'SerialVerify', 'enter', 'TeleportConfig'}
        other_sections = [s for s in sections.keys() if s not in base_sections]
        ordered_sections = other_sections + [s for s in base_sections if s in sections]

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("// ====================== 自动生成 ======================\n")
            for section_name in ordered_sections:
                typ, data = sections[section_name]
                f.write(f"\n[{section_name}]\n")
                if typ == 'dict':
                    if section_name in ConfigParser.NUMBERED_DICTS:
                        keys = sorted(data.keys(), key=lambda k: int(k) if k.isdigit() else k)
                    else:
                        keys = data.keys()
                    for key in keys:
                        f.write(f"{key} = {data[key]}\n")
                else:
                    for item in data:
                        if item:
                            f.write(f"{item}\n")
            f.write("\n// ====================== 文件结束 ======================\n")


# ===================== 列表编辑组件 =====================
class ListEditor(ttk.Frame):
    def __init__(self, parent, title, initial_list=None, height=8, **kwargs):
        super().__init__(parent, **kwargs)
        self.title = title
        self.data = initial_list.copy() if initial_list else []
        self.list_height = height
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text=self.title, font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0,5))
        frame = ttk.Frame(self)
        frame.pack(fill='both', expand=True)

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side='right', fill='y')

        self.listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, height=self.list_height)
        self.listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.listbox.yview)
        self.refresh()

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', pady=(5,0))
        ttk.Button(btn_frame, text="添加", command=self.add_item).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="编辑", command=self.edit_item).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="删除", command=self.delete_item).pack(side='left', padx=2)

    def refresh(self):
        self.listbox.delete(0, tk.END)
        for item in self.data:
            self.listbox.insert(tk.END, item)

    def add_item(self):
        from tkinter import simpledialog
        new_item = simpledialog.askstring("添加", f"输入新的{self.title}条目:")
        if new_item and new_item.strip():
            self.data.append(new_item.strip())
            self.refresh()

    def edit_item(self):
        from tkinter import simpledialog
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选中一个条目")
            return
        idx = selection[0]
        old_value = self.data[idx]
        new_value = simpledialog.askstring("编辑", "修改条目:", initialvalue=old_value)
        if new_value is not None and new_value.strip():
            self.data[idx] = new_value.strip()
            self.refresh()

    def delete_item(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选中一个条目")
            return
        idx = selection[0]
        del self.data[idx]
        self.refresh()

    def get_data(self):
        return self.data


# ===================== 字典编辑组件（双输入框） =====================
# ===================== 字典编辑组件（双向映射版） =====================
class DictEditor(ttk.Frame):
    def __init__(self, parent, title, initial_dict=None, key_label="键", value_label="值",
                 height=8, key_display_map=None, desc_map=None, key_editable=True,
                 show_desc=False, key_width=200, value_width=100, **kwargs):
        super().__init__(parent, **kwargs)
        self.title = title
        self.key_label = key_label
        self.value_label = value_label
        self.data = initial_dict.copy() if initial_dict else {}
        self.tree_height = height
        
        # 核心控制：是否允许用户增删/修改键名（GameParams 设为 False）
        self.key_editable = key_editable
        # 是否显示"说明"列（仅 GameParams / TeleportConfig 需要）
        self.show_desc = show_desc
        self.key_width = key_width
        self.value_width = value_width
        
        self.key_display_map = key_display_map or {}
        self.desc_map = desc_map or {}
        # 自动生成反向映射表（中文 -> 英文）
        self._display_to_key = {v: k for k, v in self.key_display_map.items()}
        
        self.create_widgets()
        self.bind_events()

    def _get_display_key(self, key: str) -> str:
        """获取用于界面显示的键名（英转中）"""
        return self.key_display_map.get(key, key)

    def _get_real_key(self, display: str) -> str:
        """获取用于文件存储的真实键名（中转英）"""
        return self._display_to_key.get(display, display)

    def create_widgets(self):
        ttk.Label(self, text=self.title, font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0,5))

        outer = ttk.Frame(self)
        outer.pack(fill='both', expand=True)

        tree_frame = ttk.Frame(outer)
        tree_frame.pack(fill='both', expand=True)

        v_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical')
        h_scrollbar = ttk.Scrollbar(outer, orient='horizontal')

        self.tree = ttk.Treeview(tree_frame,
                                 columns=('key', 'value', 'desc') if self.show_desc else ('key', 'value'),
                                 show='headings',
                                 yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set,
                                 height=self.tree_height)
        self.tree.heading('key', text=self.key_label)
        self.tree.heading('value', text=self.value_label)
        if self.show_desc:
            self.tree.heading('desc', text='说明')
        self.tree.column('key', width=self.key_width, minwidth=50, stretch=True)
        self.tree.column('value', width=self.value_width, minwidth=60, stretch=True)
        if self.show_desc:
            self.tree.column('desc', width=350, minwidth=150, stretch=True)
        self.tree.pack(side='left', fill='both', expand=True)

        v_scrollbar.config(command=self.tree.yview)
        v_scrollbar.pack(side='right', fill='y')
        h_scrollbar.config(command=self.tree.xview)
        h_scrollbar.pack(fill='x')

        self.refresh()

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', pady=(5,0))
        
        # 根据 key_editable 动态显示增删按钮
        if self.key_editable:
            ttk.Button(btn_frame, text="添加", command=self.add_item).pack(side='left', padx=2)
            
        ttk.Button(btn_frame, text="修改数值", command=self.edit_item).pack(side='left', padx=2)
        
        if self.key_editable:
            ttk.Button(btn_frame, text="删除", command=self.delete_item).pack(side='left', padx=2)

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="修改数值", command=self.edit_item)
        if self.key_editable:
            self.context_menu.add_command(label="删除", command=self.delete_item)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def bind_events(self):
        self.tree.bind("<Double-1>", lambda e: self.edit_item())

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for key, value in self.data.items():
            display_key = self._get_display_key(key)
            if self.show_desc:
                desc = self.desc_map.get(key, '')
                self.tree.insert('', 'end', values=(display_key, value, desc))
            else:
                self.tree.insert('', 'end', values=(display_key, value))

    def _pair_input_dialog(self, title, key_prompt, value_prompt, initial_key="", initial_value="",
                           key_readonly=False, desc_text=''):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("520x190")
        dialog.resizable(False, False)

        tk.Label(dialog, text=key_prompt).grid(row=0, column=0, padx=10, pady=(10,2), sticky='e')
        key_entry = tk.Entry(dialog, width=42)
        key_entry.grid(row=0, column=1, padx=10, pady=(10,2))
        key_entry.insert(0, initial_key)
        
        # 核心逻辑：锁定键名的输入框
        if key_readonly:
            key_entry.configure(state='readonly', readonlybackground='#f0f0f0')

        if desc_text:
            desc_label = tk.Label(dialog, text=f"💡 {desc_text}", fg='gray', font=('Arial', 9))
            desc_label.grid(row=1, column=1, padx=10, pady=(0,5), sticky='w')

        tk.Label(dialog, text=value_prompt).grid(row=2, column=0, padx=10, pady=5, sticky='e')
        value_entry = tk.Entry(dialog, width=42)
        value_entry.grid(row=2, column=1, padx=10, pady=5)
        value_entry.insert(0, initial_value)

        result = [None, None]

        def on_ok():
            k = key_entry.get().strip()
            v = value_entry.get().strip()
            if not k:
                messagebox.showwarning("警告", f"{key_prompt}不能为空")
                return
            result[0] = k
            result[1] = v
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="确定", command=on_ok).pack(side='left', padx=20)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side='left', padx=20)

        self.wait_window(dialog)
        return result[0], result[1]

    def add_item(self):
        key, value = self._pair_input_dialog(
            f"添加{self.title}映射",
            f"{self.key_label}:",
            f"{self.value_label}:"
        )
        if key is not None:
            # 新增时默认将直接输入的文本作为真实键（适用于无映射规则的情况）
            self.data[key] = value if value is not None else ""
            self.refresh()

    def edit_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选中一行")
            return
        
        display_key, old_value, desc_text = self.tree.item(selected[0], 'values') if self.show_desc else (self.tree.item(selected[0], 'values')[0], self.tree.item(selected[0], 'values')[1], '')
        real_key = self._get_real_key(display_key)
        
        # 弹窗默认显示中文（如果有映射的话）
        dialog_key = display_key if self.key_display_map else real_key
        
        key, value = self._pair_input_dialog(
            f"编辑 {self.title} 参数",
            f"{self.key_label}:",
            f"{self.value_label}:",
            initial_key=dialog_key,
            initial_value=old_value,
            key_readonly=not self.key_editable,
            desc_text=desc_text or ''
        )
        
        if key is not None:
            # 无论修改后返回什么，确保转回原生态英文键
            final_key = self._get_real_key(key)
            
            # 只有允许修改且真的改了键名的情况下，才把旧英文键删掉
            if final_key != real_key and self.key_editable:
                del self.data[real_key]
                
            self.data[final_key] = value if value is not None else ""
            self.refresh()

    def delete_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选中一行")
            return
        display_key = self.tree.item(selected[0], 'values')[0]
        real_key = self._get_real_key(display_key)
        if messagebox.askyesno("确认", f"确定删除 {self.key_label} '{display_key}' 吗？"):
            del self.data[real_key]
            self.refresh()

    def get_data(self):
        # 始终返回原始英文键名的数据，这步保证写入 configs.txt 不出错
        return self.data

    def _validate_keys(self):
        """检查 data 中是否有键不在 key_display_map 中（存在汉化映射时）"""
        if not self.key_display_map:
            return
        for key in self.data:
            if key not in self.key_display_map:
                print(f"[DictEditor] 警告: '{key}' 不在汉化映射中，界面将显示英文原名")


# ===================== GameParams 专用编辑组件 =====================
class GameParamsEditor(DictEditor):
    """
    GameParams 专用编辑器：
    - 界面显示中文参数名，文件存储英文键名（双向映射）
    - 参数名（键）只读，不可增删
    - 只允许修改参数数值
    """

    # 界面显示中文 ↔ 文件存储英文 的双向映射表
    KEY_DISPLAY_MAP = {
        'ChangeSize_Min': '大小变-最小值',
        'ChangeSize_Max': '大小变-最大值',
        'JumpJump_MinForceY': '跳一跳-最小力度',
        'JumpJump_MaxForceY': '跳一跳-最大力度',
        'JumpJump_CountPerTrigger': '跳一跳-每次触发次数',
        'MobHeal_Duration': '怪回血-持续时间(秒)',
        'MobInvisible_Duration': '怪隐身-持续时间(秒)',
        'Speed_BuffDuration': '速度变化-持续时间(秒)',
        'Speed_Normal': '速度-正常值',
        'Speed_Up': '速度-加速值',
        'Speed_Down': '速度-减速值',
        'DirectionInvert_Duration': '方向颠倒-持续时间(秒)',
        'AddHp_Ratio': '加血-比例',
        'SubHp_Ratio': '扣血-比例',
        'Curse_Amount': '诅咒-数量',
        'DoorRevenge_Count': '门复仇-每次次数',
        'LevelUp_Initial': '武器-初始等级',
        'Cells_Amount': '细胞-数量',
        'Money_Amount': '金币-数量',
        'Damage_Step': '伤害倍率-每步增减',
        'Damage_Max': '伤害倍率-上限',
        'SmallFood_Invincible': '小食物-无敌时间(秒)',
        'LargeFood_Invincible': '大食物-无敌时间(秒)',
        'RainbowMode_Duration': '幸运星-无敌时间(秒)',
        'Stun_Duration': '眩晕-持续时间(秒)',
        'ViewDown_Duration': '下移视角-持续时间(秒)',
        'Freeze_Duration': '冰冻-持续时间(秒)',
        'Shield_Duration': '护盾-持续时间(秒)',
        'ViewUp_Duration': '上移视角-持续时间(秒)',
        'Petrify_Duration': '石化-持续时间(秒)',
        'Invisible_Duration': '玩家隐身-持续时间(秒)',
        'SpeedBoost_Duration': '加速Buff-持续时间(秒)',
        'AngelHalo_Duration': '天使头环-持续时间(秒)',
        'Burn_Duration': '燃烧-持续时间(秒)',
        'Burn_Damage': '燃烧-伤害值',
        'Bleed_Duration': '流血-持续时间(秒)',
        'Bleed_Damage': '流血-伤害值',
        'Poison_Duration': '中毒-持续时间(秒)',
        'Poison_Damage': '中毒-伤害值',
    }

    # 参数说明（第三列）
    DESC_MAP = {
        'ChangeSize_Min': '玩家缩放最小倍数',
        'ChangeSize_Max': '玩家缩放最大倍数',
        'JumpJump_MinForceY': '弹跳最小纵向力度',
        'JumpJump_MaxForceY': '弹跳最大纵向力度',
        'JumpJump_CountPerTrigger': '每次触发连跳次数',
        'MobHeal_Duration': '怪物持续回血时长',
        'MobInvisible_Duration': '怪物持续隐身时长',
        'Speed_BuffDuration': '加速/减速效果持续时长',
        'Speed_Normal': '正常移动速度（默认0.23）',
        'Speed_Up': '加速时的移动速度',
        'Speed_Down': '减速时的移动速度',
        'DirectionInvert_Duration': '方向键颠倒持续时长',
        'AddHp_Ratio': '加血为最大生命的比例（0.1=10%）',
        'SubHp_Ratio': '扣血为最大生命的比例（0.2=20%）',
        'Curse_Amount': '每次施加的诅咒层数',
        'DoorRevenge_Count': '门复仇每次增加次数',
        'LevelUp_Initial': '更换武器时的初始等级',
        'Cells_Amount': '每次增加细胞数量',
        'Money_Amount': '每次增加金币数量',
        'Damage_Step': '增伤/减伤每步调整幅度',
        'Damage_Max': '伤害倍率最大上限',
        'SmallFood_Invincible': '吃小食物后无敌时长',
        'LargeFood_Invincible': '吃大食物后无敌时长',
        'RainbowMode_Duration': '幸运星彩虹闪烁+无敌时长',
        'Stun_Duration': '眩晕debuff持续时长',
        'ViewDown_Duration': '视角下移debuff持续时长',
        'Freeze_Duration': '冰冻debuff持续时长',
        'Shield_Duration': '护盾buff持续时长',
        'ViewUp_Duration': '视角上移debuff持续时长',
        'Petrify_Duration': '石化debuff持续时长',
        'Invisible_Duration': '玩家隐身buff持续时长',
        'SpeedBoost_Duration': '移速buff持续时长',
        'AngelHalo_Duration': '天使头环buff持续时长',
        'Burn_Duration': '燃烧debuff持续时长',
        'Burn_Damage': '燃烧每秒伤害值',
        'Bleed_Duration': '流血debuff持续时长',
        'Bleed_Damage': '流血每秒伤害值',
        'Poison_Duration': '中毒debuff持续时长',
        'Poison_Damage': '中毒每秒伤害值',
    }

    def __init__(self, parent, initial_dict=None, height=22, **kwargs):
        super().__init__(
            parent,
            title="游戏数值参数",
            initial_dict=initial_dict,
            key_label="参数名",
            value_label="数值",
            height=height,
            key_display_map=self.KEY_DISPLAY_MAP,
            desc_map=self.DESC_MAP,
            key_editable=False,  # 锁死：不显示添加/删除，键名只读
            show_desc=True,      # 显示说明列
            **kwargs
        )

    # get_data() 继承自 DictEditor，已自动返回英文键值对
# ===================== 主应用程序 =====================
class ConfigEditorApp:
    def __init__(self, root, config_path='configs.txt'):
        self.root = root
        self.config_path = config_path
        self.sections = {}
        self.editor_widgets = {}

        self.root.title("Dead Cells 互动模组配置工具")
        self.root.geometry("1050x850")

        self.load_config()
        self.create_top_frame()
        self.create_ui()
        ttk.Button(root, text="保存配置到文件", command=self.save_config, width=20).pack(pady=10)

    def load_config(self):
        self.sections = ConfigParser.parse(self.config_path)
        if not self.sections:
            self.init_default_sections()
        if 'BilibiliCode' not in self.sections:
            self.sections['BilibiliCode'] = ('dict', {'Code': ''})
        if 'Code' not in self.sections['BilibiliCode'][1]:
            self.sections['BilibiliCode'][1]['Code'] = ''

    def init_default_sections(self):
        defaults = {
            'BilibiliCode': ('dict', {'Code': ''}),
            'SerialVerify': ('dict', {'SerialNumber': ''}),
            'dianzan': ('list', ['加血', '随机1诅咒']),
            'enter': ('list', ['3简单怪']),          # enter 用于进房触发
            'LikeMapping': ('dict', {'诅咒': '点赞'}),
            'DanmuMapping': ('dict', {'加血': '奶一口', '加卷轴': '加卷'}),
            'DanmuLevel': ('dict', {'加卷轴': '0', '加血': '0'}),
            'GiftMapping': ('dict', {'3简单怪': '小心心'}),
            'SkinIds': ('dict', {'0': 'PrisonerDefault'}),
            'MobIds': ('list', ['LeapingDuelyst', 'Shield']),
            'ChestMonsters': ('list', ['Golem']),
            'EasyMobIds': ('list', ['Zombie']),
            'MeleeWeapons': ('dict', {'0': 'StartSword'}),
            'BagItem': ('list', ['GenericKey']),
            'Consumable': ('list', ['SmallMeat']),
            'PreciousLoot': ('list', ['SmallGem']),
            'TeleportConfig': ('dict', {'Mode': 'DepthBased'}),
            'GameParams': ('dict', {
                'ChangeSize_Min': '0.2', 'ChangeSize_Max': '5.0',
                'JumpJump_MinForceY': '0.3', 'JumpJump_MaxForceY': '1.2',
                'JumpJump_CountPerTrigger': '10',
                'MobHeal_Duration': '7', 'MobInvisible_Duration': '5',
                'Speed_BuffDuration': '5', 'Speed_Normal': '0.23',
                'Speed_Up': '0.5', 'Speed_Down': '0.1',
                'DirectionInvert_Duration': '5',
                'AddHp_Ratio': '0.1', 'SubHp_Ratio': '0.2',
                'Curse_Amount': '10', 'DoorRevenge_Count': '3',
                'LevelUp_Initial': '5', 'Cells_Amount': '10', 'Money_Amount': '10',
                'Damage_Step': '0.1', 'Damage_Max': '10.0',
                'SmallFood_Invincible': '2', 'LargeFood_Invincible': '15',
                'RainbowMode_Duration': '20',
                'Stun_Duration': '5', 'ViewDown_Duration': '3',
                'Freeze_Duration': '4', 'Shield_Duration': '8',
                'ViewUp_Duration': '3', 'Petrify_Duration': '4',
                'Invisible_Duration': '10', 'SpeedBoost_Duration': '8',
                'AngelHalo_Duration': '10',
                'Burn_Duration': '5', 'Burn_Damage': '10',
                'Bleed_Duration': '5', 'Bleed_Damage': '8',
                'Poison_Duration': '5', 'Poison_Damage': '8',
            }),
        }
        for name, (typ, data) in defaults.items():
            if name not in self.sections:
                self.sections[name] = (typ, data)

    def create_top_frame(self):
        top_frame = ttk.LabelFrame(self.root, text="⚙️ Bilibili 直播间 Code (独立配置)", padding=10)
        top_frame.pack(fill='x', padx=10, pady=5)

        code_dict = self.sections.get('BilibiliCode', ('dict', {}))[1]
        current_code = code_dict.get('Code', '')

        ttk.Label(top_frame, text="Code:").grid(row=0, column=0, padx=(0,5), pady=5, sticky='e')
        self.bili_code_var = tk.StringVar(value=current_code)
        bili_entry = ttk.Entry(top_frame, textvariable=self.bili_code_var, width=50)
        bili_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(top_frame, text="(直播间唯一标识符，请从B站获取)").grid(row=0, column=2, padx=10, pady=5, sticky='w')

        info_label = ttk.Label(top_frame, text="💡 修改后点击下方「保存配置到文件」即可生效", foreground="gray")
        info_label.grid(row=1, column=0, columnspan=3, pady=(0,5))

    def create_ui(self):
        SECTION_ZH = {
            'SerialVerify': '序列号验证',
            'dianzan': '点赞指令列表',
            'enter': '进房触发指令',          # 明确标注为进房触发
            'DanmuMapping': '弹幕映射',
            'GiftMapping': '礼物映射',
            'LikeMapping': '点赞映射',
            'DanmuLevel': '弹幕粉丝等级',
            'SkinIds': '皮肤 ID（序号从0开始）',
            'MobIds': '怪物 ID',
            'EasyMobIds': '简单怪物 ID',
            'ChestMonsters': '宝箱怪 ID',
            'MeleeWeapons': '近战武器（序号从0开始）',
            'BagItem': '背包物品',
            'Consumable': '消耗品',
            'PreciousLoot': '珍贵战利品',
            'TeleportConfig': '传送模式',
            'GameParams': '游戏数值参数',
        }

        KEY_DISPLAY_MAP = {
            'TeleportConfig': {
                'Mode': '传送模式',
            },
        }

        PARAM_DESC_MAP = {
            'TeleportConfig': {
                'Mode': 'DepthBased=深度递进 / Random=完全随机',
            },
        }

        KEY_FIXED_SECTIONS = {'TeleportConfig', 'SerialVerify'}
        REDUCED_HEIGHT = {
            'SerialVerify': 3,
            'LikeMapping': 3,
            'dianzan': 3,
            'enter': 3,
            'TeleportConfig': 4,
            'GameParams': 22,
        }

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)

        categories = {
            "映射配置": ['dianzan', 'DanmuMapping', 'GiftMapping', 'LikeMapping', 'DanmuLevel'],
            "角色/怪物ID": ['SkinIds', 'MobIds', 'EasyMobIds', 'ChestMonsters'],
            "武器列表": ['MeleeWeapons'],
            "道具列表": ['BagItem', 'Consumable', 'PreciousLoot'],
            "基础设置": ['SerialVerify', 'enter', 'TeleportConfig'],  # 基础设置放在最后保存（但界面独立）
            "游戏参数": ['GameParams'],
            "其他配置": []
        }

        all_known = []
        for cat in categories.values():
            all_known.extend(cat)
        unknown_sections = [s for s in self.sections.keys() if s not in all_known and s not in categories["其他配置"] and s != 'BilibiliCode']
        categories["其他配置"] = unknown_sections

        column_labels = {
            'DanmuMapping': ('游戏指令', '弹幕关键词'),
            'GiftMapping': ('游戏指令', '礼物关键词'),
            'LikeMapping': ('游戏指令', '点赞触发词'),
            'DanmuLevel': ('游戏指令', '粉丝等级门槛'),
            'SerialVerify': ('配置项', '值'),
            'SkinIds': ('序号', '皮肤名称'),
            'MeleeWeapons': ('序号', '武器名称'),
            'TeleportConfig': ('参数', '设定值'),
            'GameParams': ('参数名', '数值'),
        }

        for category, section_names in categories.items():
            if not section_names:
                continue
            tab = ttk.Frame(notebook)
            notebook.add(tab, text=category)

            canvas = tk.Canvas(tab)
            scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

            def on_canvas_configure(event, c=canvas, wid=window_id):
                c.itemconfig(wid, width=event.width)

            def on_frame_configure(event, c=canvas):
                c.configure(scrollregion=c.bbox("all"))

            canvas.bind("<Configure>", on_canvas_configure)
            scrollable_frame.bind("<Configure>", on_frame_configure)
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            for sec in section_names:
                if sec not in self.sections:
                    continue
                typ, data = self.sections[sec]
                zh_name = SECTION_ZH.get(sec, sec)
                frame = ttk.LabelFrame(scrollable_frame, text=f"【{zh_name}】", padding=5)
                frame.pack(fill='x', padx=5, pady=5)

                h = REDUCED_HEIGHT.get(sec, 8)
                if typ == 'list':
                    editor = ListEditor(frame, zh_name, initial_list=data, height=h)
                    editor.pack(fill='x', expand=False, pady=2)
                elif sec == 'GameParams':
                    # GameParams 使用专用子类，内部封装了所有汉化映射
                    editor = GameParamsEditor(frame, initial_dict=data)
                    editor.pack(fill='x', expand=False, pady=2)
                else:
                    key_lbl, val_lbl = column_labels.get(sec, ("键", "值"))
                    display_map = KEY_DISPLAY_MAP.get(sec, None)
                    desc_map = PARAM_DESC_MAP.get(sec, None)
                    key_editable = sec not in KEY_FIXED_SECTIONS
                    show_desc = (sec == 'TeleportConfig')  # 只有传送模式显示说明
                    # 序号列窄、名称列宽
                    key_width = 80 if '序号' in str(key_lbl) else 200
                    value_width = 260 if '序号' in str(key_lbl) else 100
                    editor = DictEditor(frame, zh_name,
                                        initial_dict=data,
                                        key_label=key_lbl,
                                        value_label=val_lbl,
                                        height=h,
                                        key_display_map=display_map,
                                        desc_map=desc_map,
                                        key_editable=key_editable,
                                        show_desc=show_desc,
                                        key_width=key_width,
                                        value_width=value_width)
                    editor.pack(fill='x', expand=False, pady=2)

                self.editor_widgets[sec] = editor

    def save_config(self):
        for sec, editor in self.editor_widgets.items():
            if sec not in self.sections:
                continue
            typ, _ = self.sections[sec]
            new_data = editor.get_data()
            self.sections[sec] = (typ, new_data)

        new_code = self.bili_code_var.get().strip()
        if 'BilibiliCode' not in self.sections:
            self.sections['BilibiliCode'] = ('dict', {})
        self.sections['BilibiliCode'] = ('dict', {'Code': new_code})

        try:
            ConfigParser.save(self.config_path, self.sections)
            messagebox.showinfo("成功", f"配置已保存至 {os.path.abspath(self.config_path)}")
        except PermissionError:
            messagebox.showerror("错误", f"没有权限写入文件：{self.config_path}\n请关闭游戏或检查文件是否被占用。")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")


if __name__ == "__main__":
    import sys
    root = tk.Tk()
    config_file = sys.argv[1] if len(sys.argv) > 1 else "configs.txt"
    app = ConfigEditorApp(root, config_file)
    root.mainloop()