import pytest
from parser.unified_parser import UnifiedParser


def test_parse_format_a():
    parser = UnifiedParser()
    text = """【地址】西湖区东日晴好
【科目】科学
【学员】初三，男，科学112/160
【时间】一周1次，一次2小时，周日
【教员】大学生-男女不限，理科生
【薪资】120元/小时"""

    job = parser.parse(text)
    assert job is not None
    assert job.address == "西湖区东日晴好"
    assert "科学" in job.subjects
    assert job.grade == "初三"
    assert job.salary == 120


def test_parse_grade_with_gender():
    parser = UnifiedParser()
    text = "【学员】：四年级，男"

    grade = parser._extract_grade(text)
    assert grade == "四年级"


def test_parse_salary_range():
    parser = UnifiedParser()
    text = "【课酬】: 140-160/h"

    salary, salary_max = parser._extract_salary(text)
    assert salary == 140
    assert salary_max == 160


def test_parse_salary_per_hour():
    parser = UnifiedParser()
    text = "薪酬：120/h"

    salary, salary_max = parser._extract_salary(text)
    assert salary == 120


def test_parse_sun_format():
    parser = UnifiedParser()
    text = """编号：[Sun]HZ26050766021
地址：[Sun]#滨江区长虹南苑
年级科目：初三科学
每周次数：1
薪酬：140-160/h"""

    job = parser.parse(text)
    assert job is not None
    assert "滨江" in job.address
    assert job.grade == "初三"
    assert job.salary == 140


def test_parse_no_data():
    parser = UnifiedParser()
    text = "今天天气不错"

    job = parser.parse(text)
    assert job is None
