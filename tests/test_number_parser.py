"""番号提取测试"""
from avdc.core.number_parser import extract_number


class TestExtractNumber:
    def test_standard(self):
        assert extract_number("SNIS-829.mp4") == "SNIS-829"

    def test_with_subtitle(self):
        assert extract_number("SNIS-829-C.mp4") == "SNIS-829"

    def test_fc2(self):
        result = extract_number("FC2-PPV-1234567.mp4")
        assert "FC2" in result
        assert "1234567" in result

    def test_fc2_no_prefix(self):
        result = extract_number("fc2-1234567.mp4")
        assert "FC2" in result

    def test_fanza_cid(self):
        assert extract_number("ssni00644.mp4") == "ssni00644"

    def test_with_date(self):
        assert extract_number("2020-01-01-SNIS-829.mp4") == "SNIS-829"

    def test_with_path(self):
        assert extract_number("/some/path/SNIS-829.mp4") == "SNIS-829"

    def test_cd_number(self):
        assert extract_number("SNIS-829-CD1.mp4") == "SNIS-829"
