import requests
import json
from parser.tutor_job import TutorJob


class AIParser:
    API_URL = "https://api.deepseek.com/chat/completions"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def parse(self, text: str) -> TutorJob | None:
        if not self.api_key:
            return None

        prompt = f"""从以下家教消息中提取信息，返回JSON格式：
{{"address": "地址", "subjects": ["科目列表"], "grade": "年级", "salary": 最低薪资数字, "salary_max": 最高薪资数字, "time": "时间要求"}}

消息：
{text[:500]}

只返回JSON，不要其他内容。"""

        try:
            response = requests.post(
                self.API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return self._parse_json_response(content, text)
        except Exception:
            pass

        return None

    def _parse_json_response(self, content: str, raw_text: str) -> TutorJob | None:
        try:
            json_str = content.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            data = json.loads(json_str)

            return TutorJob(
                id="",
                raw_text=raw_text,
                source_group="",
                address=data.get("address", ""),
                address_coords=None,
                subjects=data.get("subjects", []),
                grade=data.get("grade", ""),
                student_info="",
                time_requirement=data.get("time", ""),
                teacher_requirement="",
                salary=data.get("salary"),
                salary_max=data.get("salary_max"),
                commute_time=None,
                commute_distance=None
            )
        except Exception:
            return None
