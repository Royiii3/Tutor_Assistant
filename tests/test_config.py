import pytest
from config import load_config, UserConfig


def test_load_config_returns_user_config():
    config = load_config("config.json")
    assert isinstance(config, UserConfig)
    assert config.min_salary == 120


def test_load_config_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent.json")


def test_user_config_defaults():
    config = UserConfig(
        my_address="测试地址",
        my_coords=[120.0, 30.0],
        min_salary=100,
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
    assert config.my_address == "测试地址"
