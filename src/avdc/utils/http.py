"""HTTP 请求工具 — 带代理、重试、随机 UA、超时分离"""
from __future__ import annotations

import logging
import random
import time
from typing import Optional

import requests
from lxml import etree

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
    """复用 Session 对象，减少 TCP 握手开销"""
    global _session
    if _session is None:
        _session = requests.Session()
        conf = Config.get_instance()
        proxy = conf.proxy()
        if proxy:
            _session.proxies = {"http": f"http://{proxy}", "https": f"https://{proxy}"}
    return _session


def get_html(url: str, cookies: Optional[dict] = None, encoding: str = "utf-8") -> str:
    """
    请求网页，返回文本内容。
    失败时返回空字符串（不再返回 'ProxyError' 字符串）。
    """
    conf = Config.get_instance()
    timeout = conf.timeout()
    retry_count = conf.retry()
    session = _get_session()

    for attempt in range(1, retry_count + 1):
        try:
            headers = {"User-Agent": random.choice(_USER_AGENTS)}
            resp = session.get(
                url,
                headers=headers,
                timeout=(timeout, timeout * 2),  # (连接超时, 读取超时)
                cookies=cookies,
            )
            resp.encoding = encoding
            return resp.text
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
