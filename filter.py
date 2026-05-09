class DistrictFilter:
    def __init__(self, skip_districts: list[str]):
        self.skip_districts = [d.strip() for d in skip_districts]

    def should_skip(self, address: str) -> bool:
        if not address:
            return False
        for district in self.skip_districts:
            if district in address:
                return True
        return False

    def filter_jobs(self, jobs: list) -> list:
        return [job for job in jobs if not self.should_skip(job.address)]
