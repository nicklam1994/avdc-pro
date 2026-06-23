"""测试配置"""
import pytest
from avdc.config import Config


@pytest.fixture(autouse=True)
def reset_config():
    """每个测试前重置 Config 单例"""
    Config.reset()
    yield
    Config.reset()
