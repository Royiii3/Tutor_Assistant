import re
from parser.unified_parser import UnifiedParser
from parser.ai_parser import AIParser
from parser.tutor_job import TutorJob


class Parser:
    def __init__(self, config: dict):
        self.config = config
        self.parser = UnifiedParser()
        self.ai_parser = AIParser(config.get("deepseek_key", ""))

    def parse(self, text: str) -> TutorJob | None:
        job = self.parser.parse(text)
        if job and job.is_valid():
            return job

        if self.ai_parser.api_key:
            return self.ai_parser.parse(text)

        return None

    def parse_multiple(self, text: str) -> list[TutorJob]:
        jobs = []
        messages = self._split_messages(text)
        for msg in messages:
            msg = msg.strip()
            if len(msg) < 20:
                continue
            job = self.parse(msg)
            if job and job.is_valid():
                jobs.append(job)
        return jobs

    def _split_messages(self, text: str) -> list[str]:
        separators = [
            # Teacher prefix: "A杭州家教小姚老师:" / "A某某老师:"
            r"\n(?=A[^\n]{0,30}[：:])",
            # Common message start markers
            r"\n(?=杭州线下)",
            r"\n(?=欢杭wy\d+)",
            r"\n(?=WY杭州\d+)",
            r"\n(?=杭州ZN\d+)",
            r"\n(?=📌)",
            r"\n(?=🌟)",
            r"\n(?=♻️)",
            r"\n(?=#新单)",
            r"\n(?=#加急)",
            r"\n(?=#重新找)",
            r"\n(?=#专职单)",
            r"\n(?=#外教单)",
            # Separator lines
            r"\n{3,}",
            r"\n========+\n",
            # Numbered entries
            r"\n(?=编号[：:])",
            r"\n(?=【编号】)",
        ]

        parts = [text]
        for sep in separators:
            new_parts = []
            for part in parts:
                splits = re.split(sep, part)
                new_parts.extend(splits)
            parts = new_parts

        result = []
        for part in parts:
            part = part.strip()
            if part and len(part) >= 20:
                result.append(part)

        return result if result else [text]
