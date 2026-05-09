from parser.tutor_job import TutorJob
from config import UserConfig


class Matcher:
    def __init__(self, config: UserConfig):
        self.config = config

    def match(self, job: TutorJob) -> bool:
        if not self._check_salary(job):
            return False
        if not self._check_subjects(job):
            return False
        if not self._check_grade(job):
            return False
        if not self._check_commute_time(job):
            return False
        return True

    def _check_salary(self, job: TutorJob) -> bool:
        if not job.salary:
            return False
        effective_salary = job.salary_max if job.salary_max else job.salary
        return effective_salary >= self.config.min_salary

    def _check_subjects(self, job: TutorJob) -> bool:
        if not job.subjects:
            return True
        return any(s in self.config.subjects for s in job.subjects)

    def _check_grade(self, job: TutorJob) -> bool:
        if not job.grade:
            return True
        return job.grade in self.config.grades

    def _check_commute_time(self, job: TutorJob) -> bool:
        if job.commute_time is None:
            return True
        return job.commute_time <= self.config.max_commute_time
