"""HTTP 请求工具 — 带代理、重试、随机 UA、反爬绕过"""
from __future__ import annotations

import logging
import random
import time
from typing import Optional

import requests

from avdc.config import Config

logger = logging.getLogger(__name__)

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

_session: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    """复用 Session 对象，优先使用 cloudscraper 绕过反爬"""
    global _session
    if _session is None:
        # 尝试 cloudscraper (绕过 Cloudflare 等反爬)
        try:
            import cloudscraper
            _session = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "mobile": False}
            )
            logger.debug("使用 cloudscraper 会话")
        except ImportError:
            _session = requests.Session()
            logger.debug("使用标准 requests 会话")

        conf = Config.get_instance()
        proxy = conf.proxy()
        if proxy:
            _session.proxies = {"http": f"http://{proxy}", "https": f"https://{proxy}"}
    return _session


def reset_session() -> None:
    """重置会话（测试用或代理变更后）"""
    global _session
    _session = None


def get_html(url: str, cookies: Optional[dict] = None, encoding: str = "utf-8") -> str:
    """
    请求网页，返回文本内容。
    使用 cloudscraper 自动绕过 Cloudflare/JavBus 等反爬保护。
    失败时返回空字符串。
    """
    conf = Config.get_instance()
    timeout = conf.timeout()
    retry_count = conf.retry()
    session = _get_session()

    for attempt in range(1, retry_count + 1):
        try:
            headers = {
                "User-Agent": random.choice(_USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate",
            }
            resp = session.get(
                url,
                headers=headers,
                timeout=(timeout, timeout * 2),
                cookies=cookies,
                allow_redirects=True,
            )
            resp.encoding = encoding

            # 检测反爬页面
            text = resp.text
            if "driver-verify" in text or "captcha" in text.lower()[:1000]:
                logger.warning("检测到反爬验证页面: %s", url)
                if attempt < retry_count:
                    time.sleep(2)
                    continue
                return ""

            return text
        except requests.RequestException as e:
            logger.warning("请求失败 [%d/%d] %s: %s", attempt, retry_count, url, e)
            if attempt < retry_count:
                time.sleep(1)

    logger.error("请求彻底失败: %s", url)
    return ""


def get_xpath_single(html_str: str, xpath: str) -> str:
    """从 HTML 中提取单个 XPath 节点的文本"""
    if not html_str:
        return ""
    try:
        from lxml import etree
        tree = etree.fromstring(html_str, etree.HTMLParser())
        result = tree.xpath(xpath)
        if result:
            return str(result[0]).strip()
    except Exception as e:
        logger.debug("XPath 解析失败: %s", e)
    return ""


def get_data_state(data: dict) -> bool:
    """检查元数据是否有效（title 非空）"""
    title = data.get("title", "")
    return bool(title and title not in ("", "None", "null"))
