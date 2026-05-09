import re
from parser.tutor_job import TutorJob


class UnifiedParser:
    GRADE_KEYWORDS = [
        "幼儿园", "小班", "中班", "大班",
        "一年级", "二年级", "三年级", "四年级", "五年级", "六年级",
        "初一", "初二", "初三", "初四",
        "高一", "高二", "高三", "高中",
    ]

    SUBJECT_KEYWORDS = [
        "语文", "数学", "英语", "科学", "物理", "化学", "生物",
        "地理", "历史", "政治", "社会", "全科", "幼小衔接",
        "钢琴", "美术", "陪练", "陪读", "陪玩", "启蒙",
    ]

    def parse(self, text: str) -> TutorJob | None:
        lines = text.split("\n")

        job_id = self._extract_id(text)
        address = self._extract_address(text)
        grade = self._extract_grade(text)
        subjects = self._extract_subjects(text)
        salary, salary_max = self._extract_salary(text)
        time_req = self._extract_time(text)
        teacher_req = self._extract_teacher_requirement(text)

        if not address and not salary and not subjects:
            return None

        return TutorJob(
            id=job_id or "",
            raw_text=text,
            source_group="",
            address=address or "",
            address_coords=None,
            subjects=subjects,
            grade=grade or "",
            student_info="",
            time_requirement=time_req or "",
            teacher_requirement=teacher_req or "",
            salary=salary,
            salary_max=salary_max,
            commute_time=None,
            commute_distance=None
        )

    def _extract_id(self, text: str) -> str:
        patterns = [
            r"编号[：:]\s*\[?Sun\]?(\w+)",
            r"【编号】[：:]\s*(\w+)",
            r"WY\w+",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return ""

    def _extract_address(self, text: str) -> str:
        patterns = [
            r"地址[：:]\s*(?:\[Sun\])?#?([^\n]+)",
            r"【地址】[：:]?\s*([^\n【]+)",
            r"【辅导地点】[：:]?\s*([^\n【]+)",
            r"⭐+([^⭐\n]+)⭐+",
            # Embedded district in free text: 钱塘区下沙初三...
            r"(钱塘区|西湖区|上城区|拱墅区|滨江区|萧山区|余杭区|临平区|富阳区|临安区|海宁市|桐庐县|淳安县)[^\n，,]{0,20}",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                addr = match.group(1).strip()
                addr = addr.replace("\xa0", " ").replace("\u3000", " ")
                addr = re.sub(r"^[^\u4e00-\u9fa5]+", "", addr)
                return addr.strip()
        return ""

    def _extract_grade(self, text: str) -> str:
        for grade in self.GRADE_KEYWORDS:
            if grade in text:
                return grade
        student_match = re.search(r"【学员】[：:]?\s*([^【\n]+)", text)
        if student_match:
            student_text = student_match.group(1)
            for grade in self.GRADE_KEYWORDS:
                if grade in student_text:
                    return grade
        return ""

    def _extract_subjects(self, text: str) -> list[str]:
        subjects = []
        for keyword in self.SUBJECT_KEYWORDS:
            if keyword in text:
                if keyword == "启蒙" and "英语启蒙" in text:
                    subjects.append("英语")
                elif keyword not in subjects:
                    subjects.append(keyword)
        if not subjects:
            subject_match = re.search(r"【科目】[：:]?\s*([^\n【]+)", text)
            if subject_match:
                subject_text = subject_match.group(1)
                for keyword in self.SUBJECT_KEYWORDS:
                    if keyword in subject_text:
                        subjects.append(keyword)
        return subjects

    def _extract_salary(self, text: str) -> tuple:
        patterns = [
            # Range: 140-170元/小时, 150-180/h, 80-120元/h
            r"(\d+)\s*[-~至]\s*(\d+)\s*元?\s*/\s*(?:小时|[Hh])",
            # Range: 100-180一小时 (no slash)
            r"(\d+)\s*[-~至]\s*(\d+)\s*一?\s*小时",
            # Single: 120元/小时, 160/h
            r"(\d+)\s*元?\s*/\s*(?:小时|[Hh])",
            # Single: 150一小时
            r"(\d+)\s*一?\s*小时",
            # Per N hours: 260/2h → convert to hourly
            r"(\d+)\s*元?\s*/\s*(\d+)\s*[hH]",
            # Formatted fields
            r"【薪资】[：:]?\s*(\d+)\s*[-~至]\s*(\d+)",
            r"【课酬】[：:]?\s*(\d+)\s*[-~至]\s*(\d+)",
            r"薪酬[：:]?\s*(\d+)\s*[-~至]\s*(\d+)",
            r"【薪资】[：:]?\s*(\d+)",
            r"【课酬】[：:]?\s*(\d+)",
            r"薪酬[：:]?\s*(\d+)",
            r"【课时报酬】[：:]?\s*(\d+)\s*元?\s*/\s*(?:小时|[Hh])",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                # Per N hours: 260/2h → compute hourly
                if "/" in pattern and "[hH]" in pattern and len(groups) >= 2 and groups[1] and groups[1].isdigit() and len(groups[1]) <= 2:
                    total = int(groups[0])
                    hours = int(groups[1])
                    if hours > 1:
                        return total // hours, None
                if len(groups) >= 2 and groups[1] and groups[1].isdigit() and len(groups[1]) > 2:
                    return int(groups[0]), int(groups[1])
                elif len(groups) >= 2 and groups[1] and groups[1].isdigit():
                    return int(groups[0]), int(groups[1])
                elif groups[0]:
                    return int(groups[0]), None
        return None, None

    def _extract_time(self, text: str) -> str:
        patterns = [
            r"【时间】[：:]?\s*([^\n【]+)",
            r"【时间】[：:]\s*([^\n]+)",
            r"每周次数[：:]?\s*(\d+).*?每次时长[：:]?\s*(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_teacher_requirement(self, text: str) -> str:
        patterns = [
            r"【教员要求】[：:]?\s*([^\n【]+)",
            r"【教员】[：:]?\s*([^\n【]+)",
            r"对老师的要求[：:]?\s*([^\n#]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return ""
