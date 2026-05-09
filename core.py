import logging
from typing import Optional
from dataclasses import dataclass

from config import load_config, UserConfig
from parser.parser import Parser
from parser.tutor_job import TutorJob
from filter import DistrictFilter
from geo.geocoder import Geocoder
from geo.distance import DistanceCalculator
from matcher import Matcher
from pusher import BarkPusher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    job: TutorJob
    status: str
    reason: Optional[str] = None


class TutorAssistantCore:
    def __init__(self, config_path: str = "config.json", config: UserConfig | None = None):
        self.config: UserConfig = config if config else load_config(config_path)
        self._init_components()

    def _init_components(self):
        self.parser = Parser({
            "deepseek_key": self.config.deepseek_key,
            "amap_key": self.config.amap_key
        })
        self.district_filter = DistrictFilter(self.config.skip_districts)
        self.geocoder = Geocoder(self.config.amap_key)
        self.distance_calc = DistanceCalculator(self.config.amap_key)
        self.matcher = Matcher(self.config)
        self.pusher = BarkPusher(self.config.bark_key)
        self.my_coords = self._get_my_coords()

    def _get_my_coords(self) -> Optional[tuple]:
        if self.config.my_coords:
            return tuple(self.config.my_coords)
        coords = self.geocoder.geocode(self.config.my_address)
        if coords:
            logger.info(f"获取坐标成功: {coords}")
        return coords

    def process_text(self, text: str, source: str = "") -> list[ProcessResult]:
        results = []
        jobs = self.parser.parse_multiple(text)

        for job in jobs:
            job.source_group = source
            result = self._process_job(job)
            results.append(result)

        return results

    def _process_job(self, job: TutorJob) -> ProcessResult:
        if self.district_filter.should_skip(job.address):
            return ProcessResult(job, "skipped", "远距离区域")

        if not self.matcher.match(job):
            reasons = self._get_mismatch_reasons(job)
            return ProcessResult(job, "mismatch", reasons)

        if job.address and self.my_coords:
            coords = self.geocoder.geocode(job.address)
            if coords:
                result = self.distance_calc.calculate(
                    self.my_coords, coords, self.config.commute_mode
                )
                if result:
                    job.commute_time = result["duration"]
                    job.commute_distance = result["distance"]
                    if result["duration"] > self.config.max_commute_time:
                        return ProcessResult(job, "too_far", f"通勤{result['duration']}分钟")
                else:
                    logger.debug(f"路径计算失败: {job.address}")
            else:
                logger.debug(f"地理编码失败: {job.address}")

        success = self.pusher.push(job)
        if success:
            return ProcessResult(job, "pushed")
        else:
            return ProcessResult(job, "push_failed")

    def _get_mismatch_reasons(self, job: TutorJob) -> str:
        reasons = []
        if job.salary:
            effective = job.salary_max if job.salary_max else job.salary
            if effective < self.config.min_salary:
                reasons.append(f"薪资{effective}<{self.config.min_salary}")
        if job.subjects and not any(s in self.config.subjects for s in job.subjects):
            reasons.append(f"科目不匹配")
        if job.grade and job.grade not in self.config.grades:
            reasons.append(f"年级{job.grade}不匹配")
        return ", ".join(reasons) if reasons else "条件不符"

    def print_config(self):
        print("=" * 60)
        print("家教信息筛选配置")
        print(f"位置: {self.config.my_address}")
        print(f"坐标: {self.my_coords}")
        print(f"最低薪资: {self.config.min_salary}元/小时")
        print(f"科目: {self.config.subjects}")
        print(f"年级: {self.config.grades}")
        print(f"最大通勤: {self.config.max_commute_time}分钟 ({self.config.commute_mode})")
        print(f"跳过区域: {self.config.skip_districts}")
        print("=" * 60)
