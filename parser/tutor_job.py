from dataclasses import dataclass
from typing import Optional


@dataclass
class TutorJob:
    id: str
    raw_text: str
    source_group: str
    address: str
    address_coords: Optional[tuple[float, float]]
    subjects: list[str]
    grade: str
    student_info: str
    time_requirement: str
    teacher_requirement: str
    salary: Optional[int]
    salary_max: Optional[int]
    commute_time: Optional[int]
    commute_distance: Optional[float]

    def is_valid(self) -> bool:
        return bool(self.address and self.salary)
