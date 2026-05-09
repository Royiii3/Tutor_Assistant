import json
from dataclasses import dataclass


@dataclass
class UserConfig:
    my_address: str
    my_coords: list
    min_salary: int
    subjects: list[str]
    grades: list[str]
    max_commute_time: int
    commute_mode: str
    my_gender: str
    my_identity: str
    skip_districts: list
    target_groups: list[str]
    amap_key: str
    deepseek_key: str
    bark_key: str
    db_key: str = ""
    wechat_data_dir: str = ""


def load_config(path: str = "config.json") -> UserConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return UserConfig(**data)
