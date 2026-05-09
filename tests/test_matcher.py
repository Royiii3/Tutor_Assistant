import pytest
from parser.tutor_job import TutorJob
from matcher import Matcher
from config import UserConfig


def test_match_salary():
    config = UserConfig(
        my_address="杭州",
        my_coords=[120.0, 30.0],
        min_salary=120,
        subjects=["数学"],
        grades=["高一"],
        max_commute_time=30,
        commute_mode="电动自行车",
        my_gender="男",
        my_identity="大学生",
        skip_districts=["西湖区"],
        target_groups=[],
        amap_key="key",
        deepseek_key="key",
        bark_key="key"
    )
    matcher = Matcher(config)

    job = TutorJob(
        id="1", raw_text="", source_group="",
        address="拱墅区", address_coords=None,
        subjects=["数学"], grade="高一",
        student_info="", time_requirement="周末",
        teacher_requirement="", salary=150, salary_max=None,
        commute_time=20, commute_distance=5.0
    )

    result = matcher.match(job)
    assert result is True


def test_match_salary_too_low():
    config = UserConfig(
        my_address="杭州",
        my_coords=[120.0, 30.0],
        min_salary=150,
        subjects=["数学"],
        grades=["高一"],
        max_commute_time=30,
        commute_mode="电动自行车",
        my_gender="男",
        my_identity="大学生",
        skip_districts=["西湖区"],
        target_groups=[],
        amap_key="key",
        deepseek_key="key",
        bark_key="key"
    )
    matcher = Matcher(config)

    job = TutorJob(
        id="1", raw_text="", source_group="",
        address="拱墅区", address_coords=None,
        subjects=["数学"], grade="高一",
        student_info="", time_requirement="周末",
        teacher_requirement="", salary=100, salary_max=None,
        commute_time=20, commute_distance=5.0
    )

    result = matcher.match(job)
    assert result is False


def test_match_subject_not_in_list():
    config = UserConfig(
        my_address="杭州",
        my_coords=[120.0, 30.0],
        min_salary=120,
        subjects=["数学"],
        grades=["高一"],
        max_commute_time=30,
        commute_mode="电动自行车",
        my_gender="男",
        my_identity="大学生",
        skip_districts=["西湖区"],
        target_groups=[],
        amap_key="key",
        deepseek_key="key",
        bark_key="key"
    )
    matcher = Matcher(config)

    job = TutorJob(
        id="1", raw_text="", source_group="",
        address="拱墅区", address_coords=None,
        subjects=["语文"], grade="高一",
        student_info="", time_requirement="周末",
        teacher_requirement="", salary=150, salary_max=None,
        commute_time=20, commute_distance=5.0
    )

    result = matcher.match(job)
    assert result is False
