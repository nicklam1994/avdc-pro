"""番号提取模块 — 从文件名中提取番号（修复了原始 FC2 永真 bug）"""
from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

# 支持的视频扩展名
_VIDEO_EXTENSIONS = frozenset({
    ".mp4", ".avi", ".rmvb", ".wmv", ".mov", ".mkv", ".flv", ".ts",
})


def scan_videos(root_dir: str, escape_folders: list[str] | None = None) -> list[str]:
    """递归扫描目录，返回所有视频文件的相对路径"""
    escape = set(escape_folders or [])
    videos = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 跳过排除目录
        dirnames[:] = [d for d in dirnames if d not in escape and not d.startswith(".")]
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in _VIDEO_EXTENSIONS:
                rel = os.path.relpath(os.path.join(dirpath, f), root_dir)
                videos.append(rel)
    return videos


def extract_number(filepath: str) -> str:
    """
    从文件路径中提取番号。
    修复了原版 if 'FC2' or 'fc2' in ... 的永真 bug。
    """
    filename = os.path.basename(filepath)
    name = os.path.splitext(filename)[0]

    # 移除字幕标记
    name = name.replace("-C.", ".").replace("-c.", ".")

    # 移除 CD 编号
    part = ""
    cd_match = re.search(r"[-_](?:CD|cd)\d+", name)
    if cd_match:
        part = cd_match.group()
        name = name.replace(part, "")

    # 移除日期标记
    name = re.sub(r"\d{4}-\d{1,2}-\d{1,2}", "", name)
    name = re.sub(r"\[\d{4}-\d{1,2}-\d{1,2}\]", "", name)

    # 移除网站标记
    name = name.replace("22-sht.me", "").replace("-HD", "").replace("-hd", "")

    # 统一分隔符
    name = name.replace("_", "-")

    # === FC2 处理（修复永真 bug） ===
    name_upper = name.upper()
    if "FC2" in name_upper:  # ✅ 修复：原来的 if 'FC2' or 'fc2' in ... 永真
        name = (
            name.replace("-PPV", "").replace("PPV-", "")
            .replace("-ppv", "").replace("ppv-", "")
            .replace("FC2-", "").replace("fc2-", "")
        )
        # FC2 番号格式：FC2-PPV-1234567 或 FC2-1234567
        fc2_match = re.search(r"FC2[-_]?(?:PPV[-_]?)?(\d{5,})", name_upper)
        if fc2_match:
            return f"FC2-PPV-{fc2_match.group(1)}"
        # fallback: 尝试通用匹配
        fc2_match = re.search(r"(\d{5,})", name)
        if fc2_match:
            return f"FC2-PPV-{fc2_match.group(1)}"

    # === 带分隔符的番号 ===
    if "-" in name:
        # 标准格式：ABC-123
        match = re.search(r"([A-Za-z]+)-(\d+)", name)
        if match:
            prefix, num = match.group(1), match.group(2)
            # 检查 Tokyo Hot 特殊格式
            if "tokyo" in name.lower() and "hot" in name.lower():
                th_match = re.search(r"(cz|k|n|red-|se)\d{3,4}", name.lower())
                if th_match:
                    return th_match.group().upper()
            return f"{prefix}-{num}"
        # 数字-字母格式：12345-MMMM
        match = re.search(r"(\d+)-([A-Za-z]+)", name)
        if match:
            return match.group(0)
        # 纯数字-数字：111111-000
        match = re.search(r"(\d+)-(\d+)", name)
        if match:
            return match.group(0)

    # === 不带分隔符的番号（FANZA CID）===
    # 格式：ssni00644, abp00123
    match = re.match(r"^([A-Za-z]{2,})(\d{3,})$", name)
    if match:
        prefix, num = match.group(1), match.group(2)
        # 如果前缀长且数字短，加分隔符
        if len(prefix) > 1 and len(num) <= 4:
            return f"{prefix}-{num}"
        return name

    # === 最终 fallback ===
    return name
