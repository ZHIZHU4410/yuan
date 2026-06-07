import threading
import time
import math
import pyautogui
from pynput import keyboard, mouse
from utils import game_compatible_move, SLEEP_INTERVAL


class ComboProfile:
    """连招配置类"""
    def __init__(self, name, hotkey, sequence, repeat=1):
        self.name = name
        self.hotkey = hotkey
        self.sequence = sequence
        self.repeat = repeat
        self.is_running = False
        self.stop_event = threading.Event()
        self.thread = None


class MacroController:
    def __init__(self, getters, label_setters):
        self.getters = getters
        self.set_label = label_setters

        # 基础功能状态
        self.running_states = {'click': False, 'move': False, 'rotate': False}
        self.events = {k: threading.Event() for k in self.running_states}
        
        # 连招管理
        self.combos = []  # ComboProfile 列表
        self.combo_map = {}  # hotkey -> ComboProfile 映射，用于快速查找
        
        self.hotkey_listener = None
        
        # 累积位移变量
        self.accum_x = self.accum_y = self.rot_accum = 0.0
        
        # 状态改变回调
        self.state_changed_callback = None
        # 全局连招总开关，默认开启
        self.global_switch = True
        self.global_switch_callback = None
    def toggle_global_switch(self):
        """切换总开关状态，关闭时会停止所有连招，开启时仅恢复热键响应"""
        self.global_switch = not self.global_switch
        if not self.global_switch:
            # 总开关关闭时，立即停止所有正在运行的连招
            self.stop_all_combos()
        # 通知 UI 更新显示
        if self.global_switch_callback:
            self.global_switch_callback(self.global_switch)

    def set_global_switch_callback(self, callback):
        """设置总开关状态改变时的回调，参数为 enabled (bool)"""
        self.global_switch_callback = callback

    def set_state_changed_callback(self, callback):
        """设置连招状态改变时的回调函数，回调参数为 profile"""
        self.state_changed_callback = callback

    def get(self, key):
        getter = self.getters.get(key)
        return getter() if callable(getter) else None

    def add_combo(self, profile):
        """添加连招"""
        self.combos.append(profile)
        self.combo_map[profile.hotkey] = profile

    def remove_combo(self, profile):
        """移除连招"""
        if profile in self.combos:
            # 如果正在运行，先停止
            if profile.is_running:
                self.stop_combo(profile)
            self.combos.remove(profile)
            if profile.hotkey in self.combo_map:
                del self.combo_map[profile.hotkey]

    def update_combo_hotkey(self, profile, old_hotkey):
        """更新连招的热键"""
        if old_hotkey in self.combo_map:
            del self.combo_map[old_hotkey]
        self.combo_map[profile.hotkey] = profile

    def get_combo_state(self, profile):
        """获取连招状态"""
        return profile.is_running

    def is_hotkey_used(self, hotkey):
        """检查热键是否已被使用"""
        # 检查基础功能（这里需要从 getters 获取，实际调用时传入）
        return hotkey in self.combo_map

    def toggle_combo(self, profile):
        """切换连招运行状态（受全局总开关影响）"""
        if not self.global_switch:
            # 总开关关闭时，连招热键无效
            return
        if profile.is_running:
            self.stop_combo(profile)
        else:
            self.start_combo(profile)

    def start_combo(self, profile):
        """启动连招"""
        if profile.is_running:
            return
        
        profile.is_running = True
        profile.stop_event.clear()
        profile.thread = threading.Thread(target=self.combo_worker, args=(profile,), daemon=True)
        profile.thread.start()
        # 通知 UI 状态变化
        if self.state_changed_callback:
            self.state_changed_callback(profile)

    def stop_combo(self, profile):
        """停止连招"""
        if not profile.is_running:
            return
        
        profile.is_running = False
        profile.stop_event.set()
        if profile.thread and profile.thread.is_alive():
            profile.thread.join(timeout=0.5)
        # 通知 UI 状态变化
        if self.state_changed_callback:
            self.state_changed_callback(profile)

    # ---------- 新增：将字符串键名转换为 pynput 键对象 ----------
    def _str_to_key(self, key_str):
        """将字符串键名转换为 pynput 可接受的键对象（单个字符或 Key 枚举）"""
        if key_str is None:
            return None
        # 长度==1的普通字符
        if len(key_str) == 1:
            return key_str.lower()   # pynput 接受小写字母
        # 特殊键映射表
        special_map = {
            'SPACE': keyboard.Key.space,
            'ENTER': keyboard.Key.enter,
            'RETURN': keyboard.Key.enter,
            'SHIFT': keyboard.Key.shift,
            'LSHIFT': keyboard.Key.shift_l,
            'RSHIFT': keyboard.Key.shift_r,
            'CTRL': keyboard.Key.ctrl,
            'LCTRL': keyboard.Key.ctrl_l,
            'RCTRL': keyboard.Key.ctrl_r,
            'ALT': keyboard.Key.alt,
            'LALT': keyboard.Key.alt_l,
            'RALT': keyboard.Key.alt_r,
            'WIN': keyboard.Key.cmd,
            'BACKSPACE': keyboard.Key.backspace,
            'TAB': keyboard.Key.tab,
            'CAPSLOCK': keyboard.Key.caps_lock,
            'DELETE': keyboard.Key.delete,
            'HOME': keyboard.Key.home,
            'END': keyboard.Key.end,
            'PAGEUP': keyboard.Key.page_up,
            'PAGEDOWN': keyboard.Key.page_down,
            'UP': keyboard.Key.up,
            'DOWN': keyboard.Key.down,
            'LEFT': keyboard.Key.left,
            'RIGHT': keyboard.Key.right,
            'F1': keyboard.Key.f1,
            'F2': keyboard.Key.f2,
            'F3': keyboard.Key.f3,
            'F4': keyboard.Key.f4,
            'F5': keyboard.Key.f5,
            'F6': keyboard.Key.f6,
            'F7': keyboard.Key.f7,
            'F8': keyboard.Key.f8,
            'F9': keyboard.Key.f9,
            'F10': keyboard.Key.f10,
            'F11': keyboard.Key.f11,
            'F12': keyboard.Key.f12,
        }
        up_key = key_str.upper()
        if up_key in special_map:
            return special_map[up_key]
        # 如果无法映射，回退为小写字符串
        return key_str.lower()

    # ---------- 连招工作线程 ----------
    def combo_worker(self, profile):
        """连招工作线程"""
        raw_seq = profile.sequence.strip()
        
        # 解析连招
        if raw_seq.startswith('{'):
            steps = self.parse_raw_macro(raw_seq)
        else:
            steps = self.parse_simple_macro(raw_seq)
        
        if not steps:
            profile.is_running = False
            if self.state_changed_callback:
                self.state_changed_callback(profile)
            return
        
        kb_controller = keyboard.Controller()
        ms_controller = mouse.Controller()
        mouse_btn_map = {'left': mouse.Button.left, 'right': mouse.Button.right, 'middle': mouse.Button.middle}
        
        for _ in range(profile.repeat):
            if profile.stop_event.is_set() or not profile.is_running:
                break
            
            for typ, param, wait in steps:
                if profile.stop_event.is_set() or not profile.is_running:
                    break
                
                try:
                    if typ == 'key_down':
                        key = self._str_to_key(param)
                        if key is not None:
                            kb_controller.press(key)
                    elif typ == 'key_up':
                        key = self._str_to_key(param)
                        if key is not None:
                            kb_controller.release(key)
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
        
        profile.is_running = False
        if self.state_changed_callback:
            self.state_changed_callback(profile)

    # ---------- 解析简单格式 ----------
    def parse_simple_macro(self, text):
        """解析简单格式的连招 (分号分隔)"""
        items = text.split(';')
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
                if action in ('left_click', 'right_click', 'middle_click'):
                    base = action.split('_')[0]
                    steps.append(('mouse_down', base, 0))
                    steps.append(('wait', None, hold))
                    steps.append(('mouse_up', base, 0))
                    steps.append(('wait', None, interval))
                else:
                    steps.append(('key_down', action, 0))
                    steps.append(('wait', None, hold))
                    steps.append(('key_up', action, 0))
                    steps.append(('wait', None, interval))
        
        return steps

    # ---------- 解析花括号高级格式（扩展支持 D/U 后缀） ----------
    def parse_raw_macro(self, text):
        """解析花括号格式的连招，扩展支持 {KeyD}/{KeyU} 和特殊键名"""
        steps = []
        i = 0
        n = len(text)
        # 鼠标专有指令（不应被键盘D/U解析器干扰）
        mouse_buttons = {'LMB': 'left', 'RMB': 'right', 'MMB': 'middle'}
        mouse_down_ups = {'LMBD', 'LMBU', 'RMBD', 'RMBU', 'MMBD', 'MMBU'}
        
        while i < n:
            if text[i] == '{':
                j = text.find('}', i)
                if j == -1:
                    break
                cmd = text[i+1:j].strip()
                i = j + 1
                
                # 1. 等待指令
                if cmd.startswith('WAITMS:'):
                    ms = int(cmd.split(':')[1])
                    steps.append(('wait', None, ms / 1000.0))
                
                # 2. HOLDMS:xxx 指令（保持一个键）
                elif cmd.startswith('HOLDMS:'):
                    parts = cmd.split(':')
                    ms = int(parts[1])
                    # 跳过空白
                    while i < n and text[i] in (' ', '\t', '\r', '\n'):
                        i += 1
                    if i < n and text[i] != '{':
                        key_char = text[i]
                        i += 1
                    else:
                        key_char = None
                    if key_char:
                        steps.append(('key_down', key_char, 0))
                        steps.append(('wait', None, ms / 1000.0))
                        steps.append(('key_up', key_char, 0))
                
                # 3. 鼠标操作（单击、按下、抬起）
                elif cmd in mouse_buttons:
                    btn = mouse_buttons[cmd]
                    steps.append(('mouse_down', btn, 0))
                    steps.append(('mouse_up', btn, 0))
                elif cmd in mouse_down_ups:
                    if cmd == 'LMBD':
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
                
                # 4. 键盘操作：支持 {KeyD} 按下, {KeyU} 抬起, 以及 {Key} 单击
                else:
                    # 检查是否是 D 或 U 结尾的键盘指令
                    if len(cmd) >= 2 and cmd[-1] in ('D', 'U'):
                        key = cmd[:-1]          # 去掉最后一个字母
                        if cmd[-1] == 'D':
                            steps.append(('key_down', key, 0))
                        else:  # 'U'
                            steps.append(('key_up', key, 0))
                    elif len(cmd) == 1:
                        # 单字符键：按下并立即抬起（单击）
                        steps.append(('key_down', cmd, 0))
                        steps.append(('key_up', cmd, 0))
                    else:
                        # 其他未知指令忽略（可打印警告）
                        pass
            else:
                i += 1
        
        return steps

    def toggle_click(self):
        state = not self.running_states['click']
        self.running_states['click'] = state
        if state:
            self.events['click'].clear()
            self.set_label('click', '🟢 连点运行中', 'green')
            threading.Thread(target=self.click_loop, daemon=True).start()
        else:
            self.events['click'].set()
            self.set_label('click', '● 已停止', 'gray')

    def click_loop(self):
        while not self.events['click'].is_set() and self.running_states['click']:
            pyautogui.click(_pause=False)
            try:
                time.sleep(1.0 / float(self.get('freq')))
            except Exception:
                break

    def stop_all_combos(self):
        """停止所有连招"""
        for profile in self.combos:
            if profile.is_running:
                self.stop_combo(profile)

    def start_all_combos(self):
        """启动所有连招"""
        for profile in self.combos:
            if not profile.is_running:
                self.start_combo(profile)

    # ========== 基础功能：平移 ==========
    def toggle_move(self):
        state = not self.running_states['move']
        self.running_states['move'] = state
        if state:
            self.events['move'].clear()
            self.accum_x = self.accum_y = 0.0
            self.set_label('move', '🟢 平移移动中', 'green')
            threading.Thread(target=self.move_loop, daemon=True).start()
        else:
            self.events['move'].set()
            self.set_label('move', '● 已停止', 'gray')

    def move_loop(self):
        dir_map = {"上":(0,-1),"下":(0,1),"左":(-1,0),"右":(1,0),
                   "左上":(-1,-1),"右上":(1,-1),"左下":(-1,1),"右下":(1,1)}
        last_time = time.perf_counter()
        while not self.events['move'].is_set() and self.running_states['move']:
            dt = time.perf_counter() - last_time
            last_time = time.perf_counter()
            try:
                dx, dy = dir_map.get(self.get('dir_move'), (0,0))
                mag = math.hypot(dx, dy)
                if mag > 0:
                    dx, dy = dx/mag, dy/mag
                self.accum_x += float(self.get('speed_move')) * dt * dx
                self.accum_y += float(self.get('speed_move')) * dt * dy
                ix, iy = int(self.accum_x), int(self.accum_y)
                if ix or iy:
                    game_compatible_move(ix, iy)
                    self.accum_x -= ix
                    self.accum_y -= iy
            except Exception:
                break
            time.sleep(SLEEP_INTERVAL)

    # ========== 基础功能：视角旋转 ==========
    def toggle_rotate(self):
        state = not self.running_states['rotate']
        self.running_states['rotate'] = state
        if state:
            self.events['rotate'].clear()
            self.rot_accum = 0.0
            self.set_label('rotate', '🟢 视角旋转中', 'green')
            threading.Thread(target=self.rotate_loop, daemon=True).start()
        else:
            self.events['rotate'].set()
            self.set_label('rotate', '● 已停止', 'gray')

    def rotate_loop(self):
        last_time = time.perf_counter()
        while not self.events['rotate'].is_set() and self.running_states['rotate']:
            curr_time = time.perf_counter()
            dt = curr_time - last_time
            last_time = curr_time
            try:
                speed = float(self.get('speed_rot'))
                direction = -1 if "左" in self.get('dir_rot') else 1
                step_x = speed * dt * direction
                self.rot_accum += step_x
                int_x = int(self.rot_accum)
                if int_x:
                    game_compatible_move(int_x, 0)
                    self.rot_accum -= int_x
            except Exception:
                break
            time.sleep(SLEEP_INTERVAL)

    # ========== 热键注册 ==========
    def register_hotkeys(self, mapping):
        """注册全局热键"""
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
        
        try:
            self.hotkey_listener = keyboard.GlobalHotKeys(mapping)
            self.hotkey_listener.start()
        except Exception as e:
            raise

    def stop_all(self):
        """停止所有功能"""
        for k in list(self.running_states.keys()):
            self.running_states[k] = False
            self.events[k].set()
        
        for profile in self.combos:
            if profile.is_running:
                self.stop_combo(profile)
        
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass