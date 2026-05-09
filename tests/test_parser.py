import pytest
from parser.parser import Parser


def test_parser_detects_format_a():
    parser = Parser(config={"deepseek_key": "", "amap_key": ""})
    text = "【地址】西湖区\n【科目】数学\n【薪资】120元/小时"
    job = parser.parse(text)
    assert job is not None
    assert job.address == "西湖区"
    assert job.subjects == ["数学"]


def test_parser_detects_star_format():
    parser = Parser(config={"deepseek_key": "", "amap_key": ""})
    text = "⭐⭐拱墅区⭐⭐\n初三数学 160/h"
    job = parser.parse(text)
    assert job is not None
    assert "拱墅" in job.address


def test_parser_split_multiple():
    parser = Parser(config={"deepseek_key": "", "amap_key": ""})
    text = """编号：123
地址：拱墅区
薪资：120/h

编号：456
地址：滨江区
薪资：150/h"""

    jobs = parser.parse_multiple(text)
    assert len(jobs) >= 1


def test_parser_no_data():
    parser = Parser(config={"deepseek_key": "", "amap_key": ""})
    text = "今天天气不错"
    job = parser.parse(text)
    assert job is None
