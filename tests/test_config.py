"""配置管理测试"""
from avdc.config import Config


class TestConfig:
    def test_default_values(self):
        conf = Config()  # config.ini 不存在时使用默认值
        assert conf.main_mode() == 1
        assert conf.timeout() == 7
        assert conf.failed_folder() == "failed"

    def test_singleton(self):
        c1 = Config.get_instance()
        c2 = Config.get_instance()
        assert c1 is c2

    def test_sources_default(self):
        conf = Config()
        sources = conf.sources()
        assert "javbus" in sources
        assert "javdb" in sources
