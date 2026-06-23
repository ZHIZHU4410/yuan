"""
扫雷游戏 - 经典 Windows 扫雷的 Python + tkinter 实现
"""
import tkinter as tk
from tkinter import messagebox
import random
import time


# ============================================================
#  核心游戏逻辑
# ============================================================
class MinesweeperGame:
    """扫雷核心逻辑（纯数据，不含 GUI）"""

    LEVELS = {
        "初级": {"rows": 9, "cols": 9, "mines": 10},
        "中级": {"rows": 16, "cols": 16, "mines": 40},
        "高级": {"rows": 16, "cols": 30, "mines": 99},
    }

    def __init__(self, level="初级"):
        self.reset(level)

    # -------- 重置 --------
    def reset(self, level=None):
        if level:
            self.level = level
        cfg = self.LEVELS[self.level]
        self.rows = cfg["rows"]
        self.cols = cfg["cols"]
        self.total_mines = cfg["mines"]

        self.first_click = True       # 首次点击安全
        self.game_over = False
        self.win = False

        # minefield: -1=地雷, 0~8=周围地雷数
        self.minefield = [[0] * self.cols for _ in range(self.rows)]
        # revealed[r][c] = True/False
        self.revealed = [[False] * self.cols for _ in range(self.rows)]
        # flagged[r][c] = True/False
        self.flagged = [[False] * self.cols for _ in range(self.rows)]

        self.remaining_mines = self.total_mines
        self.revealed_count = 0

    # -------- 布雷（首次点击后执行，保证首点安全）--------
    def _place_mines(self, safe_r, safe_c):
        """在排除 (safe_r, safe_c) 3×3 范围后随机布雷"""
        candidates = []
        for r in range(self.rows):
            for c in range(self.cols):
                if abs(r - safe_r) <= 1 and abs(c - safe_c) <= 1:
                    continue
                candidates.append((r, c))

        mine_positions = random.sample(candidates, self.total_mines)
        for r, c in mine_positions:
            self.minefield[r][c] = -1

        # 计算数字
        for r in range(self.rows):
            for c in range(self.cols):
                if self.minefield[r][c] == -1:
                    continue
                self.minefield[r][c] = self._count_adjacent_mines(r, c)

    def _count_adjacent_mines(self, r, c):
        count = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    if self.minefield[nr][nc] == -1:
                        count += 1
        return count

    # -------- 操作 --------
    def reveal(self, r, c):
        """左键点击揭露格子，返回被揭露的格子列表 [(r,c),...]"""
        if self.game_over:
            return []
        if self.revealed[r][c] or self.flagged[r][c]:
            return []

        # 首次点击 → 布雷
        if self.first_click:
            self._place_mines(r, c)
            self.first_click = False

        revealed_cells = []
        self._reveal_recursive(r, c, revealed_cells)

        # 踩雷判断
        if self.minefield[r][c] == -1:
            self.game_over = True
            self.win = False
            return revealed_cells

        # 胜利判断
        total_safe = self.rows * self.cols - self.total_mines
        if self.revealed_count >= total_safe:
            self.game_over = True
            self.win = True

        return revealed_cells

    def _reveal_recursive(self, r, c, revealed_cells):
        """递归揭露：空块自动展开"""
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return
        if self.revealed[r][c] or self.flagged[r][c]:
            return

        self.revealed[r][c] = True
        self.revealed_count += 1
        revealed_cells.append((r, c))

        # 如果是空白（周围 0 颗雷），递归展开邻居
        if self.minefield[r][c] == 0:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    self._reveal_recursive(r + dr, c + dc, revealed_cells)

    def toggle_flag(self, r, c):
        """右键标记/取消旗帜"""
        if self.game_over or self.revealed[r][c]:
            return

        if self.flagged[r][c]:
            self.flagged[r][c] = False
            self.remaining_mines += 1
        else:
            self.flagged[r][c] = True
            self.remaining_mines -= 1

    def reveal_all_mines(self):
        """游戏结束时揭露所有地雷"""
        for r in range(self.rows):
            for c in range(self.cols):
                if self.minefield[r][c] == -1:
                    self.revealed[r][c] = True

    # -------- 双击快速展开 --------
    def quick_reveal(self, r, c):
        """双击数字格快速展开相邻格。返回 (revealed_cells, hit_mine)"""
        if self.game_over:
            return [], None
        if not self.revealed[r][c]:
            return [], None
        if self.minefield[r][c] <= 0:
            return [], None

        # 统计相邻旗帜数
        adj_flags = 0
        for nr, nc in self.neighbors(r, c):
            if self.flagged[nr][nc]:
                adj_flags += 1

        if adj_flags != self.minefield[r][c]:
            return [], None

        # 展开所有未揭露、未标记的邻居
        revealed_cells = []
        hit_cell = None
        for nr, nc in self.neighbors(r, c):
            if not self.revealed[nr][nc] and not self.flagged[nr][nc]:
                result = self.reveal(nr, nc)
                revealed_cells.extend(result)
                if self.game_over and not self.win:
                    hit_cell = (nr, nc)

        # 再次判断胜利
        total_safe = self.rows * self.cols - self.total_mines
        if self.revealed_count >= total_safe:
            self.game_over = True
            self.win = True

        return revealed_cells, hit_cell

    # -------- 遍历邻居 --------
    def neighbors(self, r, c):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    yield nr, nc


# ============================================================
#  GUI
# ============================================================
class MinesweeperGUI:
    """扫雷 GUI（tkinter）"""

    # 颜色方案
    NUMBER_COLORS = {
        1: "#0000FF", 2: "#008000", 3: "#FF0000", 4: "#000080",
        5: "#800000", 6: "#008080", 7: "#000000", 8: "#808080",
    }

    CELL_W = 30   # 单元格像素宽
    CELL_H = 30

    def __init__(self, root):
        self.root = root
        self.root.title("扫雷")
        self.root.resizable(False, False)

        self.game = MinesweeperGame("初级")
        self.buttons = {}          # (r,c) -> tk.Button
        self.timer_running = False
        self.start_time = 0
        self.timer_id = None
        self.elapsed = 0

        self._build_menu()
        self._build_header()
        self._build_grid()
        self._center_window()

    # ==================== 菜单栏 ====================
    def _build_menu(self):
        menubar = tk.Menu(self.root)
        game_menu = tk.Menu(menubar, tearoff=0)
        for level in ("初级", "中级", "高级"):
            game_menu.add_command(
                label=level,
                command=lambda lv=level: self._restart(lv),
            )
        game_menu.add_separator()
        game_menu.add_command(label="自定义…", command=self._custom_difficulty)
        game_menu.add_separator()
        game_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="游戏", menu=game_menu)
        self.root.config(menu=menubar)

    # ==================== 顶部面板 ====================
    def _build_header(self):
        header = tk.Frame(self.root, bg="#C0C0C0")
        header.pack(pady=5)

        # 剩余雷数
        self.mine_label = tk.Label(
            header, text=str(self.game.remaining_mines),
            font=("Consolas", 18, "bold"), bg="#000000", fg="#FF0000",
            width=4, relief=tk.SUNKEN,
        )
        self.mine_label.pack(side=tk.LEFT, padx=10)

        # 笑脸按钮
        self.face_btn = tk.Button(
            header, text="🙂", font=("Segoe UI Emoji", 16),
            width=3, height=1, command=lambda: self._restart(),
        )
        self.face_btn.pack(side=tk.LEFT, padx=20)

        # 计时器
        self.time_label = tk.Label(
            header, text="0",
            font=("Consolas", 18, "bold"), bg="#000000", fg="#FF0000",
            width=4, relief=tk.SUNKEN,
        )
        self.time_label.pack(side=tk.LEFT, padx=10)

    # ==================== 雷区网格 ====================
    def _build_grid(self):
        self.grid_frame = tk.Frame(self.root, bg="#808080")
        self.grid_frame.pack(padx=10, pady=5)
        self._populate_grid()

    def _populate_grid(self):
        """根据当前游戏状态创建/刷新按钮网格"""
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        self.buttons.clear()

        for r in range(self.game.rows):
            for c in range(self.game.cols):
                btn = tk.Button(
                    self.grid_frame,
                    text="",
                    width=2, height=1,
                    font=("Microsoft YaHei", 10, "bold"),
                    bg="#C0C0C0", relief=tk.RAISED,
                    command=lambda rr=r, cc=c: self._on_left_click(rr, cc),
                )
                btn.bind("<Button-3>", lambda e, rr=r, cc=c: self._on_right_click(rr, cc))
                btn.bind("<Double-Button-1>", lambda e, rr=r, cc=c: self._on_double_click(rr, cc))
                btn.grid(row=r, column=c, sticky="nsew")
                self.buttons[(r, c)] = btn

    # ==================== 事件处理 ====================
    def _on_left_click(self, r, c):
        if self.game.game_over:
            return

        # 首次点击时启动计时器
        if self.game.first_click and not self.timer_running:
            self._start_timer()

        revealed = self.game.reveal(r, c)
        for rr, cc in revealed:
            self._update_button(rr, cc)

        if self.game.game_over:
            self._stop_timer()
            if self.game.win:
                self._on_win()
            else:
                self._on_lose(r, c)

    def _on_right_click(self, r, c):
        if self.game.game_over:
            return
        self.game.toggle_flag(r, c)
        self._update_button(r, c)
        self.mine_label.config(text=str(self.game.remaining_mines))

    def _update_button(self, r, c):
        """根据游戏状态更新单个按钮外观"""
        btn = self.buttons.get((r, c))
        if btn is None:
            return

        if self.game.revealed[r][c]:
            btn.config(relief=tk.SUNKEN, bg="#D0D0D0")
            val = self.game.minefield[r][c]
            if val == -1:
                btn.config(text="💣", fg="#000000")
            elif val > 0:
                btn.config(
                    text=str(val),
                    fg=self.NUMBER_COLORS.get(val, "#000000"),
                )
            else:
                btn.config(text="")
        elif self.game.flagged[r][c]:
            btn.config(text="🚩", fg="#FF0000")
        else:
            btn.config(text="", relief=tk.RAISED, bg="#C0C0C0")

    def _on_double_click(self, r, c):
        """双击已揭露数字格 → 快速展开相邻格"""
        if self.game.game_over:
            return
        if not self.game.revealed[r][c]:
            return

        revealed, hit_cell = self.game.quick_reveal(r, c)
        for rr, cc in revealed:
            self._update_button(rr, cc)

        if self.game.game_over:
            self._stop_timer()
            if self.game.win:
                self._on_win()
            elif hit_cell:
                self._on_lose(*hit_cell)

    def _show_centered_dialog(self, title, message):
        """在游戏窗口正中央弹出自定义对话框"""
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        frame = tk.Frame(dlg, padx=30, pady=20)
        frame.pack()

        tk.Label(frame, text=message, font=("Microsoft YaHei", 12),
                 justify=tk.CENTER).pack(pady=(0, 15))

        btn = tk.Button(frame, text="确定", width=10, font=("Microsoft YaHei", 10),
                        command=dlg.destroy)
        btn.pack()

        # 先更新以获取尺寸，然后居中于主窗口
        dlg.update_idletasks()
        dw = dlg.winfo_reqwidth()
        dh = dlg.winfo_reqheight()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        x = rx + (rw - dw) // 2
        y = ry + (rh - dh) // 2
        dlg.geometry(f"+{x}+{y}")

        btn.focus_set()
        dlg.bind("<Return>", lambda e: dlg.destroy())
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.wait_window()

    def _on_win(self):
        self.face_btn.config(text="😎")
        self.game.reveal_all_mines()
        for r, c in self.buttons:
            self._update_button(r, c)
        self._show_centered_dialog("恭喜！", f"你赢了！\n用时：{self.elapsed} 秒")

    def _on_lose(self, clicked_r, clicked_c):
        self.face_btn.config(text="😵")
        self.game.reveal_all_mines()
        for r, c in self.buttons:
            self._update_button(r, c)
        # 踩中的雷高亮标记
        btn = self.buttons.get((clicked_r, clicked_c))
        if btn:
            btn.config(bg="#FF0000")

    # ==================== 计时器 ====================
    def _start_timer(self):
        self.timer_running = True
        self.start_time = time.time()
        self._tick()

    def _tick(self):
        if not self.timer_running:
            return
        self.elapsed = int(time.time() - self.start_time)
        self.time_label.config(text=str(min(self.elapsed, 999)))
        self.timer_id = self.root.after(200, self._tick)

    def _stop_timer(self):
        self.timer_running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

    # ==================== 自定义难度 ====================
    def _custom_difficulty(self):
        """弹出自定义难度对话框"""
        dlg = tk.Toplevel(self.root)
        dlg.title("自定义难度")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        frame = tk.Frame(dlg, padx=20, pady=15)
        frame.pack()

        # 行数
        tk.Label(frame, text="行数 (9~30) ：", font=("Microsoft YaHei", 10)).grid(
            row=0, column=0, sticky="e", pady=6)
        row_var = tk.IntVar(value=16)
        tk.Spinbox(frame, from_=9, to=30, textvariable=row_var,
                   width=6, font=("Microsoft YaHei", 10)).grid(
            row=0, column=1, sticky="w", pady=6)

        # 列数
        tk.Label(frame, text="列数 (9~50) ：", font=("Microsoft YaHei", 10)).grid(
            row=1, column=0, sticky="e", pady=6)
        col_var = tk.IntVar(value=30)
        tk.Spinbox(frame, from_=9, to=50, textvariable=col_var,
                   width=6, font=("Microsoft YaHei", 10)).grid(
            row=1, column=1, sticky="w", pady=6)

        # 雷数
        tk.Label(frame, text="雷数 (10~999)：", font=("Microsoft YaHei", 10)).grid(
            row=2, column=0, sticky="e", pady=6)
        mine_var = tk.IntVar(value=99)
        tk.Spinbox(frame, from_=10, to=999, textvariable=mine_var,
                   width=6, font=("Microsoft YaHei", 10)).grid(
            row=2, column=1, sticky="w", pady=6)

        # 按钮
        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(12, 0))

        def on_ok():
            rows = row_var.get()
            cols = col_var.get()
            mines = mine_var.get()
            max_mines = rows * cols - 9  # 保留 3×3 安全区
            if mines < 1:
                mines = 1
            if mines > max_mines:
                mines = max_mines
            dlg.destroy()
            # 以自定义参数启动新局
            self._restart(custom=(rows, cols, mines))

        tk.Button(btn_frame, text="确定", width=8, font=("Microsoft YaHei", 10),
                  command=on_ok).pack(side=tk.LEFT, padx=8)
        tk.Button(btn_frame, text="取消", width=8, font=("Microsoft YaHei", 10),
                  command=dlg.destroy).pack(side=tk.LEFT, padx=8)

        # 居中于主窗口
        dlg.update_idletasks()
        dw = dlg.winfo_reqwidth()
        dh = dlg.winfo_reqheight()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        x = rx + (rw - dw) // 2
        y = ry + (rh - dh) // 2
        dlg.geometry(f"+{x}+{y}")
        dlg.bind("<Return>", lambda e: on_ok())
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.wait_window()

    # ==================== 重置 ====================
    def _restart(self, level=None, custom=None):
        self._stop_timer()
        self.elapsed = 0
        self.time_label.config(text="0")
        self.face_btn.config(text="🙂")

        if custom:
            rows, cols, mines = custom
            self.game.LEVELS["自定义"] = {"rows": rows, "cols": cols, "mines": mines}
            self.game.reset("自定义")
        else:
            self.game.reset(level)

        # 更新剩余雷数显示
        self.mine_label.config(text=str(self.game.remaining_mines))

        # 刷新网格
        self._populate_grid()

        # 只在首次启动时居中，重开时保留当前位置
        if not hasattr(self, '_initial_centered'):
            self._center_window()
            self._initial_centered = True

    def _center_window(self):
        """让窗口居中显示（仅首次启动时调用）"""
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"+{x}+{y}")


# ============================================================
#  入口
# ============================================================
def main():
    root = tk.Tk()
    app = MinesweeperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
