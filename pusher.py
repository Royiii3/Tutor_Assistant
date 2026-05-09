import requests
from parser.tutor_job import TutorJob


class BarkPusher:
    API_URL_TEMPLATE = "https://api.day.app/{device_key}/{content}"

    def __init__(self, device_keys: str):
        self.device_keys = self._parse_keys(device_keys)

    def _parse_keys(self, keys_str: str) -> list[str]:
        if not keys_str or keys_str == "YOUR_BARK_KEY":
            return []
        
        raw_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        parsed = []
        for key in raw_keys:
            key = key.rstrip("/")
            if "/" in key:
                key = key.split("/")[-1]
            if key:
                parsed.append(key)
        return parsed

    def build_message(self, job: TutorJob) -> str:
        salary_text = f"{job.salary}"
        if job.salary_max:
            salary_text = f"{job.salary}-{job.salary_max}"
        salary_text += "元/h"

        commute_text = ""
        if job.commute_time:
            commute_text = f"通勤约 {job.commute_time} 分钟"
            if job.commute_distance:
                commute_text += f" ({job.commute_distance}km)"

        subjects_text = " ".join(job.subjects) if job.subjects else ""

        lines = [
            f"[{subjects_text}] {job.grade}" if subjects_text else job.grade,
            f"地址: {job.address}",
            f"薪资: {salary_text}",
        ]
        if commute_text:
            lines.append(f"通勤: {commute_text}")
        if job.time_requirement:
            lines.append(f"时间: {job.time_requirement}")

        return "\n".join(lines)

    def push(self, job: TutorJob) -> bool:
        if not self.device_keys:
            print("Bark推送未配置，跳过推送")
            return False

        try:
            from urllib.parse import quote

            message = self.build_message(job)
            title = f"新家教 - {job.address}"

            success_count = 0
            for key in self.device_keys:
                title_enc = quote(title, safe="")
                body_enc = quote(message, safe="")
                url = f"https://api.day.app/{key}/{title_enc}/{body_enc}"

                response = requests.get(url, timeout=10)
                data = response.json()

                if data.get("code") == 200:
                    success_count += 1
                else:
                    print(f"Bark推送失败 (设备{key[:8]}...): {data}")

            return success_count > 0
        except Exception as e:
            print(f"Bark推送异常: {e}")
            return False
