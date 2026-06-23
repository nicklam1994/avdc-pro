"""瀏覽器引擎 — Playwright 繞過 Cloudflare 等反爬保護"""
from __future__ import annotations

import logging
import time
from typing import Optional

from avdc.config import Config

logger = logging.getLogger(__name__)

_browser = None
_context = None


def _get_browser():
    """獲取或創建瀏覽器實例（單例）"""
    global _browser, _context
    if _browser is None:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        _browser = pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        _context = _browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        # 注入反檢測腳本
        _context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'ja', 'en'] });
        """)
    return _context


def get_html_browser(url: str, wait_selector: str = "", timeout: int = 15000) -> str:
    """
    使用 Playwright 瀏覽器獲取頁面 HTML。
    自動等待 Cloudflare 驗證完成。
    
    Args:
        url: 目標 URL
        wait_selector: 等待出現的 CSS 選擇器（可選）
        timeout: 超時毫秒數
    """
    context = _get_browser()
    page = context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)

        # 等待 Cloudflare 驗證（通常 5 秒內完成）
        for _ in range(10):
            title = page.title()
            if "Just a moment" not in title and "Cloudflare" not in title:
                break
            time.sleep(1)
        else:
            logger.warning("Cloudflare 驗證超時: %s", url)
            return ""

        # 等待特定元素
        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=5000)
            except Exception:
                pass  # 超時繼續

        return page.content()
    except Exception as e:
        logger.error("瀏覽器請求失敗 %s: %s", url, e)
        return ""
    finally:
        page.close()


def close_browser() -> None:
    """關閉瀏覽器"""
    global _browser, _context
    if _browser:
        _browser.close()
        _browser = None
        _context = None
