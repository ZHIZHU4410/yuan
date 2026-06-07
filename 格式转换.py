# -*- coding: utf-8 -*-
"""
多格式转换工具 —— 支持图片 & 音乐文件批量互转
=================================================
图片格式：PNG, JPG, BMP, WEBP, TIFF, GIF, ICO
音频格式：MP3, WAV, OGG, FLAC, AAC, M4A

依赖：
    pip install Pillow
    pip install pydub         (音频转换需要 FFmpeg 在 PATH 中)
"""

import os
import sys
import glob
from pathlib import Path
from datetime import datetime

# ==================== 图片转换 ====================
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

IMG_FORMATS = {
    ".png":  "PNG",
    ".jpg":  "JPEG",
    ".jpeg": "JPEG",
    ".bmp":  "BMP",
    ".webp": "WEBP",
    ".tiff": "TIFF",
    ".tif":  "TIFF",
    ".gif":  "GIF",
    ".ico":  "ICO",
}

IMG_QUALITY_PARAMS = {
    "JPEG": {"quality": 95, "optimize": True},
    "WEBP": {"quality": 90, "lossless": False},
    "PNG":  {"compress_level": 6},
}


def convert_image(src_path: str, dst_path: str, target_ext: str, quality: int = 90) -> bool:
    """将单张图片转换为目标格式"""
    if not HAS_PIL:
        print("  ❌ 未安装 Pillow，请运行: pip install Pillow")
        return False

    fmt = IMG_FORMATS.get(target_ext.lower(), target_ext.upper().lstrip("."))
    try:
        img = Image.open(src_path)

        # GIF 动图处理：取第一帧
        if getattr(img, "is_animated", False):
            img.seek(0)

        # 透明通道处理：JPEG/BMP 不支持 alpha
        if fmt in ("JPEG", "BMP") and img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif img.mode == "P":
            img = img.convert("RGBA")

        save_kwargs = {}
        if fmt in IMG_QUALITY_PARAMS:
            save_kwargs = dict(IMG_QUALITY_PARAMS[fmt])
            if fmt == "JPEG":
                save_kwargs["quality"] = quality
            elif fmt == "WEBP":
                save_kwargs["quality"] = quality

        img.save(dst_path, format=fmt, **save_kwargs)
        return True
    except Exception as e:
        print(f"  ❌ 转换失败 [{src_path}]: {e}")
        return False


# ==================== 音频转换 ====================
try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

# ==================== FFmpeg 检测 ====================
import subprocess
import shutil

def check_ffmpeg() -> bool:
    """检测 FFmpeg 是否可用"""
    # 优先检查 pydub 是否能找到 ffmpeg
    if HAS_PYDUB:
        try:
            from pydub.utils import get_ffmpeg_exe, get_prober_name
            ffmpeg_exe = get_ffmpeg_exe()
            if ffmpeg_exe and os.path.exists(ffmpeg_exe):
                return True
        except Exception:
            pass
    # 回退：直接检查 PATH 中是否有 ffmpeg
    return shutil.which("ffmpeg") is not None

def get_ffmpeg_install_hint() -> str:
    """获取 FFmpeg 安装提示"""
    return (
        "🔊 未检测到 FFmpeg，音频转换功能不可用。\n"
        "   Windows 安装方法（任选一种）：\n"
        "   1. winget install ffmpeg    （推荐，自动加入 PATH）\n"
        "   2. choco install ffmpeg     （需要 Chocolatey）\n"
        "   3. 手动下载: https://ffmpeg.org/download.html\n"
        "      解压后将 bin 目录添加到系统 PATH 环境变量，然后重启终端。\n"
        "   💡 安装后请在终端运行 ffmpeg -version 验证。"
    )

HAS_FFMPEG = check_ffmpeg()

AUDIO_FORMATS = {
    ".mp3":  "mp3",
    ".wav":  "wav",
    ".ogg":  "ogg",
    ".flac": "flac",
    ".aac":  "aac",
    ".m4a":  "mp4",   # pydub 用 mp4 处理 m4a
    ".wma":  "wma",
}

AUDIO_BITRATE = {
    "mp3":  "192k",
    "ogg":  "160k",
    "aac":  "192k",
    "mp4":  "192k",
    "wma":  "192k",
}


def convert_audio(src_path: str, dst_path: str, target_ext: str, bitrate: str = "192k") -> bool:
    """将单个音频文件转换为目标格式"""
    if not HAS_PYDUB:
        print("  ❌ 未安装 pydub，请运行: pip install pydub")
        print(get_ffmpeg_install_hint())
        return False
    if not HAS_FFMPEG:
        print("  ❌ 未检测到 FFmpeg，无法转换音频")
        print(get_ffmpeg_install_hint())
        return False

    fmt = AUDIO_FORMATS.get(target_ext.lower(), target_ext.lower().lstrip("."))
    try:
        audio = AudioSegment.from_file(src_path)
        export_kwargs = {"format": fmt}
        if fmt in AUDIO_BITRATE:
            export_kwargs["bitrate"] = bitrate

        audio.export(dst_path, **export_kwargs)
        return True
    except Exception as e:
        print(f"  ❌ 转换失败 [{src_path}]: {e}")
        if "WinError 2" in str(e) or "找不到" in str(e):
            print(get_ffmpeg_install_hint())
        return False


# ==================== 核心调度 ====================
def detect_media_type(ext: str) -> str:
    """根据扩展名判断文件类型"""
    ext = ext.lower()
    if ext in IMG_FORMATS:
        return "image"
    if ext in AUDIO_FORMATS:
        return "audio"
    return "unknown"


def batch_convert(
    folder: str,
    target_format: str,
    source_formats: list = None,
    recursive: bool = True,
    quality: int = 90,
    bitrate: str = "192k",
    delete_original: bool = False,
) -> dict:
    """
    批量转换文件夹中的媒体文件
    返回 {'success': int, 'failed': int, 'skipped': int}
    """
    target_ext = target_format if target_format.startswith(".") else f".{target_format}"
    media_type = detect_media_type(target_ext)

    if media_type == "unknown":
        print(f"❌ 不支持的目标格式: {target_format}")
        return {"success": 0, "failed": 0, "skipped": 0}

    # 检查依赖
    if media_type == "image" and not HAS_PIL:
        print("❌ 图片转换需要 Pillow: pip install Pillow")
        return {"success": 0, "failed": 0, "skipped": 0}
    if media_type == "audio" and not HAS_PYDUB:
        print("❌ 音频转换需要 pydub: pip install pydub")
        return {"success": 0, "failed": 0, "skipped": 0}
    if media_type == "audio" and not HAS_FFMPEG:
        print("❌ 音频转换需要 FFmpeg")
        print(get_ffmpeg_install_hint())
        return {"success": 0, "failed": 0, "skipped": 0}

    folder_path = Path(folder)
    if not folder_path.is_dir():
        print(f"❌ 文件夹不存在: {folder}")
        return {"success": 0, "failed": 0, "skipped": 0}

    # 构建搜索模式
    if source_formats:
        patterns = []
        for fmt in source_formats:
            f = fmt if fmt.startswith(".") else f".{fmt}"
            patterns.append(f"**/*{f}" if recursive else f"*{f}")
    else:
        # 默认：搜索该媒体类型的所有支持格式
        fmt_map = IMG_FORMATS if media_type == "image" else AUDIO_FORMATS
        patterns = []
        for ext in fmt_map:
            patterns.append(f"**/*{ext}" if recursive else f"*{ext}")

    # 收集文件（排除已是目标格式的文件）
    files_to_convert = []
    seen = set()
    for pattern in patterns:
        for f in folder_path.glob(pattern):
            if f.is_file() and f.suffix.lower() != target_ext.lower():
                abs_path = str(f.resolve())
                if abs_path not in seen:
                    seen.add(abs_path)
                    files_to_convert.append(f)

    if not files_to_convert:
        print(f"📭 未找到可转换的文件（目标格式: {target_ext}）")
        return {"success": 0, "failed": 0, "skipped": 0}

    print(f"\n{'='*60}")
    print(f"📁 文件夹: {folder}")
    print(f"🎯 目标格式: {target_ext}  |  文件数: {len(files_to_convert)}")
    if delete_original:
        print(f"⚠️  模式: 转换后删除原文件")
    print(f"{'='*60}\n")

    stats = {"success": 0, "failed": 0, "skipped": 0}
    convert_func = convert_image if media_type == "image" else convert_audio

    for i, src in enumerate(files_to_convert, 1):
        dst = src.with_suffix(target_ext)

        # 跳过已存在的目标文件
        if dst.exists():
            print(f"  ⏭ [{i}/{len(files_to_convert)}] 已存在，跳过: {dst.name}")
            stats["skipped"] += 1
            continue

        print(f"  🔄 [{i}/{len(files_to_convert)}] {src.name} -> {dst.name}")

        # 执行转换
        if media_type == "image":
            ok = convert_image(str(src), str(dst), target_ext, quality)
        else:
            ok = convert_audio(str(src), str(dst), target_ext, bitrate)

        if ok:
            stats["success"] += 1
            # 删除原文件
            if delete_original:
                try:
                    src.unlink()
                    print(f"      🗑 已删除原文件")
                except Exception as e:
                    print(f"      ⚠️ 删除原文件失败: {e}")
        else:
            stats["failed"] += 1
            # 清理失败的目标文件
            if dst.exists():
                dst.unlink()

    print(f"\n{'='*60}")
    print(f"✅ 成功: {stats['success']}  |  ❌ 失败: {stats['failed']}  |  ⏭ 跳过: {stats['skipped']}")
    print(f"{'='*60}")
    return stats


# ==================== 交互式命令行 ====================
def interactive_cli():
    """命令行交互模式"""
    print("=" * 60)
    print("       🎨 多格式媒体转换工具 🎵")
    print("=" * 60)

    # 选择媒体类型
    print("\n请选择要转换的媒体类型:")
    print("  [1] 图片 (PNG/JPG/BMP/WEBP/TIFF/GIF/ICO)")
    print("  [2] 音频 (MP3/WAV/OGG/FLAC/AAC/M4A)")
    choice = input("输入序号 (1/2): ").strip()

    if choice == "1":
        media_type = "image"
        fmt_map = IMG_FORMATS
        print("\n支持的图片格式:", ", ".join(set(IMG_FORMATS.values())))
    elif choice == "2":
        media_type = "audio"
        fmt_map = AUDIO_FORMATS
        if not HAS_PYDUB:
            print("\n⚠️  警告: 未安装 pydub，音频转换不可用")
            print("请运行: pip install pydub")
            print(get_ffmpeg_install_hint())
            return
        if not HAS_FFMPEG:
            print("\n⚠️  警告: 未检测到 FFmpeg，音频转换不可用")
            print(get_ffmpeg_install_hint())
            return
        print("\n支持的音频格式:", ", ".join(set(AUDIO_FORMATS.values())))
    else:
        print("无效选择！")
        return

    # 目标格式
    all_exts = sorted(set(fmt_map.keys()))
    print(f"\n可选扩展名: {', '.join(all_exts)}")
    target = input("目标格式 (如 .png 或 mp3): ").strip().strip(".")
    if not target:
        print("未输入目标格式，退出。")
        return

    # 源文件夹
    folder = input("源文件夹路径: ").strip().strip('"')
    if not os.path.isdir(folder):
        print(f"❌ 文件夹不存在: {folder}")
        return

    # 是否递归
    recur = input("包含子文件夹? (y/n, 默认 y): ").strip().lower()
    recursive = recur != "n"

    # 源格式过滤
    print(f"\n可选源格式 (留空=全部): {', '.join(all_exts)}")
    src_fmt_input = input("源格式 (多个用逗号分隔，如 .png,.jpg): ").strip()
    source_formats = None
    if src_fmt_input:
        source_formats = [f.strip() for f in src_fmt_input.split(",") if f.strip()]

    # 质量 / 比特率
    if media_type == "image":
        q = input("JPEG/WEBP 质量 (1-100, 默认 90): ").strip()
        quality = int(q) if q.isdigit() and 1 <= int(q) <= 100 else 90
        bitrate = "192k"
    else:
        br = input("比特率 (如 128k, 192k, 320k, 默认 192k): ").strip()
        bitrate = br if br else "192k"
        quality = 90

    # 是否删除原文件
    delete_confirm = input("⚠️  转换后删除原文件? (y/n, 默认 n): ").strip().lower()
    delete_original = delete_confirm == "y"

    # 执行
    batch_convert(
        folder=folder,
        target_format=target,
        source_formats=source_formats,
        recursive=recursive,
        quality=quality,
        bitrate=bitrate,
        delete_original=delete_original,
    )

    input("\n按 Enter 退出...")


# ==================== GUI 模式 ====================
def launch_gui():
    """启动图形界面"""
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog

    class MediaConverterGUI:
        def __init__(self, root):
            self.root = root
            self.root.title("多格式媒体转换工具")
            self.root.geometry("700x720")
            self.root.resizable(True, True)
            self.root.minsize(650, 650)

            style = ttk.Style()
            style.theme_use("clam")
            style.configure("TLabel", font=("Microsoft YaHei", 10))
            style.configure("TButton", font=("Microsoft YaHei", 10), padding=5)
            style.configure("TLabelframe.Label", font=("Microsoft YaHei", 11, "bold"))
            style.configure("Title.TLabel", font=("Microsoft YaHei", 14, "bold"), foreground="#2980b9")
            style.configure("Count.TLabel", font=("Microsoft YaHei", 9, "bold"), foreground="#27ae60")

            self.media_type = tk.StringVar(value="image")
            self.target_format = tk.StringVar(value=".png")
            self.folder_path = tk.StringVar()
            self.recursive = tk.BooleanVar(value=True)
            self.quality = tk.IntVar(value=90)
            self.bitrate = tk.StringVar(value="192k")
            self.source_filter = tk.StringVar()
            self.found_files = []     # 扫描到的文件路径列表
            self._scan_job = None     # 延迟扫描定时器

            self.build_ui()

        # ==================== UI 构建 ====================
        def build_ui(self):
            # 标题
            ttk.Label(self.root, text="🎨 多格式媒体转换工具 🎵", style="Title.TLabel").pack(pady=8)

            # === 第1行：媒体类型 + 目标格式 ===
            row1 = ttk.Frame(self.root)
            row1.pack(fill="x", padx=15, pady=3)

            type_frame = ttk.LabelFrame(row1, text="媒体类型", padding=8)
            type_frame.pack(side="left", fill="x", expand=True, padx=(0, 5))
            ttk.Radiobutton(type_frame, text="🖼 图片", variable=self.media_type,
                            value="image", command=self.on_type_change).pack(side="left", padx=15)
            ttk.Radiobutton(type_frame, text="🎵 音频", variable=self.media_type,
                            value="audio", command=self.on_type_change).pack(side="left", padx=15)

            fmt_frame = ttk.LabelFrame(row1, text="目标格式", padding=8)
            fmt_frame.pack(side="left", fill="x", padx=(5, 0))
            self.fmt_combo = ttk.Combobox(fmt_frame, textvariable=self.target_format,
                                          state="readonly", width=12)
            self.fmt_combo.pack(side="left", padx=5)
            self.update_format_list()

            # === 第2行：文件夹选择 + 扫描按钮 ===
            dir_frame = ttk.LabelFrame(self.root, text="📁 源文件夹", padding=8)
            dir_frame.pack(fill="x", padx=15, pady=3)
            self.folder_entry = ttk.Entry(dir_frame, textvariable=self.folder_path)
            self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
            ttk.Button(dir_frame, text="📂 浏览...", command=self.browse_folder).pack(side="left", padx=2)
            ttk.Button(dir_frame, text="🔍 扫描文件", command=self.scan_files).pack(side="left", padx=2)

            # 文件夹变动时自动扫描
            self.folder_path.trace_add("write", lambda *a: self._schedule_scan())

            # === 第3行：选项 ===
            opt_frame = ttk.LabelFrame(self.root, text="⚙ 选项", padding=8)
            opt_frame.pack(fill="x", padx=15, pady=3)

            opt_top = ttk.Frame(opt_frame)
            opt_top.pack(fill="x")
            ttk.Checkbutton(opt_top, text="包含子文件夹", variable=self.recursive,
                            command=self.scan_files).pack(side="left", padx=(0, 20))

            ttk.Label(opt_top, text="源格式过滤:").pack(side="left")
            self.filter_entry = ttk.Entry(opt_top, textvariable=self.source_filter, width=20)
            self.filter_entry.pack(side="left", padx=5)
            ttk.Label(opt_top, text="(逗号分隔，留空=全部)", foreground="gray").pack(side="left")
            self.source_filter.trace_add("write", lambda *a: self._schedule_scan())

            # 质量/比特率
            opt_bot = ttk.Frame(opt_frame)
            opt_bot.pack(fill="x", pady=(5, 0))

            self.quality_frame = ttk.Frame(opt_bot)
            self.quality_frame.pack(side="left", padx=(0, 20))
            ttk.Label(self.quality_frame, text="质量:").pack(side="left")
            ttk.Scale(self.quality_frame, from_=10, to=100, variable=self.quality,
                      orient="horizontal", length=120).pack(side="left", padx=5)
            ttk.Label(self.quality_frame, textvariable=self.quality, width=3,
                      font=("Microsoft YaHei", 9, "bold")).pack(side="left")

            self.bitrate_frame = ttk.Frame(opt_bot)
            self.bitrate_frame.pack(side="left")
            ttk.Label(self.bitrate_frame, text="比特率:").pack(side="left")
            ttk.Combobox(self.bitrate_frame, textvariable=self.bitrate,
                         values=["64k", "96k", "128k", "160k", "192k", "256k", "320k"],
                         state="readonly", width=7).pack(side="left", padx=5)
            self.bitrate_frame.pack_forget()

            # === 第4行：文件列表标题 + 统计 ===
            list_header = ttk.Frame(self.root)
            list_header.pack(fill="x", padx=15, pady=(8, 0))
            ttk.Label(list_header, text="📋 待转换文件列表", style="TLabelframe.Label").pack(side="left")
            self.file_count_label = ttk.Label(list_header, text="", style="Count.TLabel")
            self.file_count_label.pack(side="right")

            # === 文件列表（Treeview） ===
            list_frame = ttk.Frame(self.root)
            list_frame.pack(fill="both", expand=True, padx=15, pady=3)

            columns = ("filename", "folder")
            self.file_tree = ttk.Treeview(list_frame, columns=columns, show="headings",
                                          selectmode="extended", height=10)
            self.file_tree.heading("filename", text="文件名", anchor="w")
            self.file_tree.heading("folder", text="所在文件夹", anchor="w")
            self.file_tree.column("filename", width=250, minwidth=150)
            self.file_tree.column("folder", width=400, minwidth=200)

            tree_scroll_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_tree.yview)
            tree_scroll_x = ttk.Scrollbar(list_frame, orient="horizontal", command=self.file_tree.xview)
            self.file_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

            self.file_tree.grid(row=0, column=0, sticky="nsew")
            tree_scroll_y.grid(row=0, column=1, sticky="ns")
            tree_scroll_x.grid(row=1, column=0, sticky="ew")
            list_frame.grid_rowconfigure(0, weight=1)
            list_frame.grid_columnconfigure(0, weight=1)

            # 提示占位
            self.file_tree.insert("", "end", values=("👆 请先选择文件夹，然后点击「扫描文件」", ""))

            # === 操作按钮 ===
            btn_frame = ttk.Frame(self.root)
            btn_frame.pack(pady=8)
            self.convert_btn = ttk.Button(btn_frame, text="🚀 开始转换", command=self.start_convert, width=18)
            self.convert_btn.pack(side="left", padx=5)
            ttk.Button(btn_frame, text="🔄 刷新列表", command=self.scan_files, width=12).pack(side="left", padx=5)
            ttk.Button(btn_frame, text="📋 依赖说明", command=self.show_deps, width=12).pack(side="left", padx=5)

            # === 状态栏 ===
            self.status_var = tk.StringVar(value="就绪 — 请选择文件夹并扫描")
            ttk.Label(self.root, textvariable=self.status_var, relief="sunken",
                      anchor="w", padding=4).pack(fill="x", side="bottom")

        # ==================== 事件处理 ====================
        def _schedule_scan(self):
            """延迟 500ms 自动扫描，避免每次按键都触发"""
            if self._scan_job is not None:
                self.root.after_cancel(self._scan_job)
            self._scan_job = self.root.after(500, self.scan_files)

        def on_type_change(self):
            self.update_format_list()
            if self.media_type.get() == "audio":
                self.quality_frame.pack_forget()
                self.bitrate_frame.pack(side="left")
            else:
                self.bitrate_frame.pack_forget()
                self.quality_frame.pack(side="left", padx=(0, 20))
            self.scan_files()

        def update_format_list(self):
            if self.media_type.get() == "image":
                exts = sorted(set(IMG_FORMATS.keys()))
                self.fmt_combo["values"] = exts
                self.target_format.set(".png")
            else:
                exts = sorted(set(AUDIO_FORMATS.keys()))
                self.fmt_combo["values"] = exts
                self.target_format.set(".mp3")

        def browse_folder(self):
            path = filedialog.askdirectory(title="选择源文件夹")
            if path:
                self.folder_path.set(path)
                self.scan_files()

        # ==================== 文件扫描 ====================
        def scan_files(self):
            """扫描文件夹中的可转换文件，填充列表"""
            folder = self.folder_path.get().strip()
            self.file_tree.delete(*self.file_tree.get_children())
            self.found_files = []

            if not folder or not os.path.isdir(folder):
                if folder:
                    self.file_tree.insert("", "end", values=("❌ 文件夹不存在", folder))
                else:
                    self.file_tree.insert("", "end", values=("👆 请先选择文件夹，然后点击「扫描文件」", ""))
                self.file_count_label.config(text="")
                self.status_var.set("请选择文件夹并扫描")
                return

            folder_path = Path(folder)
            target_ext = self.target_format.get().strip().lower()
            recursive = self.recursive.get()
            media_type = self.media_type.get()
            fmt_map = IMG_FORMATS if media_type == "image" else AUDIO_FORMATS

            # 解析源格式过滤
            sf = self.source_filter.get().strip()
            if sf:
                allowed = set()
                for f in sf.split(","):
                    f = f.strip()
                    if f:
                        allowed.add(f if f.startswith(".") else f".{f}")
                allowed_lower = {a.lower() for a in allowed}
            else:
                allowed_lower = None

            # 扫描
            found = []
            all_exts = set(fmt_map.keys())
            for ext in sorted(all_exts):
                pattern = f"**/*{ext}" if recursive else f"*{ext}"
                for f in folder_path.glob(pattern):
                    if f.is_file() and f.suffix.lower() != target_ext:
                        if allowed_lower is None or f.suffix.lower() in allowed_lower:
                            found.append(f)

            self.found_files = sorted(found, key=lambda x: x.name.lower())

            # 填充 Treeview
            if not self.found_files:
                supported = ", ".join(sorted(all_exts))
                hint = f"📭 未找到可转换文件"
                self.file_tree.insert("", "end", values=(hint, f"支持格式: {supported}"))
                self.file_count_label.config(text="0 个文件")
                self.status_var.set(f"未找到文件 — 支持格式: {supported}")
            else:
                # 按格式统计
                type_count = {}
                for f in self.found_files:
                    ext = f.suffix.lower()
                    type_count[ext] = type_count.get(ext, 0) + 1
                summary = ", ".join(f"{ext}({cnt})" for ext, cnt in sorted(type_count.items()))

                for f in self.found_files:
                    self.file_tree.insert("", "end", values=(f.name, str(f.parent)))

                self.file_count_label.config(
                    text=f"共 {len(self.found_files)} 个文件  [{summary}]"
                )
                self.status_var.set(f"已扫描到 {len(self.found_files)} 个文件，就绪")

        # ==================== 转换 ====================
        def start_convert(self):
            folder = self.folder_path.get().strip()
            if not folder:
                messagebox.showwarning("提示", "请先选择源文件夹！")
                return
            if not os.path.isdir(folder):
                messagebox.showerror("错误", f"文件夹不存在:\n{folder}")
                return
            if not self.found_files:
                messagebox.showwarning("提示", "没有找到可转换的文件！\n请先点击「扫描文件」检查。")
                return

            target = self.target_format.get().strip()

            sf = self.source_filter.get().strip()
            source_formats = None
            if sf:
                source_formats = [f.strip() for f in sf.split(",") if f.strip()]

            self.status_var.set("转换中...")
            self.convert_btn.config(state="disabled")

            import threading
            import builtins
            original_print = builtins.print

            def log_print(*args, **kwargs):
                msg = " ".join(str(a) for a in args)
                self.root.after(0, lambda m=msg: self._append_log(m))
                original_print(*args, **kwargs)

            def run():
                builtins.print = log_print
                try:
                    stats = batch_convert(
                        folder=folder,
                        target_format=target,
                        source_formats=source_formats,
                        recursive=self.recursive.get(),
                        quality=self.quality.get(),
                        bitrate=self.bitrate.get(),
                        delete_original=False,
                    )
                    self.root.after(0, lambda: self.status_var.set(
                        f"✅ 完成 — 成功:{stats['success']}  失败:{stats['failed']}  跳过:{stats['skipped']}"
                    ))
                    self.root.after(0, lambda: self.convert_btn.config(state="normal"))
                    self.root.after(100, self.scan_files)  # 刷新列表
                except Exception as e:
                    self.root.after(0, lambda: self._append_log(f"❌ 异常: {e}"))
                    self.root.after(0, lambda: self.status_var.set("❌ 出错"))
                    self.root.after(0, lambda: self.convert_btn.config(state="normal"))
                finally:
                    builtins.print = original_print

            t = threading.Thread(target=run, daemon=True)
            t.start()

        def _append_log(self, msg: str):
            """线程安全地追加日志"""
            self.file_tree.delete(*self.file_tree.get_children())
            self.file_tree.insert("", "end", values=(msg, ""))
            self.file_tree.yview_moveto(1)
            self.root.update_idletasks()

        def show_deps(self):
            messagebox.showinfo("依赖说明",
                                "📦 图片转换: pip install Pillow\n"
                                "📦 音频转换: pip install pydub\n"
                                "🔊 音频需 FFmpeg: https://ffmpeg.org/download.html\n\n"
                                "当前已安装:\n"
                                f"  Pillow:  {'✅' if HAS_PIL else '❌ 未安装'}\n"
                                f"  pydub:   {'✅' if HAS_PYDUB else '❌ 未安装'}\n"
                                f"  FFmpeg:  {'✅ 已检测到' if HAS_FFMPEG else '❌ 未检测到'}")

    root = tk.Tk()
    app = MediaConverterGUI(root)
    root.mainloop()


# ==================== 入口 ====================
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 命令行模式: python 格式转换.py <文件夹> <目标格式> [选项]
        import argparse

        parser = argparse.ArgumentParser(description="多格式媒体转换工具")
        parser.add_argument("folder", help="源文件夹路径")
        parser.add_argument("target", help="目标格式 (如 .png, .mp3)")
        parser.add_argument("-s", "--source", help="源格式过滤 (逗号分隔)")
        parser.add_argument("-nr", "--no-recursive", action="store_true", help="不包含子文件夹")
        parser.add_argument("-q", "--quality", type=int, default=90, help="图片质量 1-100")
        parser.add_argument("-b", "--bitrate", default="192k", help="音频比特率")
        parser.add_argument("-d", "--delete", action="store_true", help="转换后删除原文件")
        parser.add_argument("--gui", action="store_true", help="强制启动 GUI")

        args = parser.parse_args()

        if args.gui:
            launch_gui()
        else:
            source_formats = None
            if args.source:
                source_formats = [f.strip() for f in args.source.split(",") if f.strip()]

            batch_convert(
                folder=args.folder,
                target_format=args.target,
                source_formats=source_formats,
                recursive=not args.no_recursive,
                quality=args.quality,
                bitrate=args.bitrate,
                delete_original=args.delete,
            )
    else:
        # 无参数时启动 GUI
        print("启动 GUI 模式... (可使用 --help 查看命令行用法)")
        launch_gui()
