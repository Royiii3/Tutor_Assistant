# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

家教信息自动筛选系统 — monitors WeChat tutor-group messages, parses tutoring job listings, filters them by salary/subject/grade/commute-time, and pushes matches to your phone via Bark.

## Commands

```bash
pip install -r requirements.txt
pytest tests/ -v                          # all tests
pytest tests/test_parser.py -v            # single test file
python paste.py                           # read clipboard → parse → push (no browser)
python paste.py file.txt                  # read from file
python paste.py --no-push                 # parse only, don't push
python streamlit run streamlit_app.py     # web paste UI (http://localhost:8501)
python main.py [config.json]              # live DB-polling mode
```

## Architecture

**Entry**: `main.py` → `TutorAssistant.run()` creates `TutorAssistantCore` + `WeChatListener`.

**Processing pipeline** (`core.py:_process_job`): `Parser.parse_multiple()` → per-job: `DistrictFilter.should_skip()` → `Matcher.match()` → `Geocoder.geocode()` + `DistanceCalculator.calculate()` → `BarkPusher.push()`.

**Message source** (`wechat_listener.py`): three-tier fallback:
1. DB polling — `db/db_reader.py` reads the local encrypted WeChat SQLite database (sqlcipher3 + key).
2. Legacy DLL hook — ComWeChatRobot (may be blocked by recent WeChat versions).
3. Mock mode — no-op loop.

**DB access** (`db/`):
- `key_extractor.py` — finds the SQLCipher encryption key from WeChat process memory (pymem) or cached file. Falls back to known derivation methods for older WeChat versions. Key is cached at `~/.wechat_tutor_dbkey`.
- `db_reader.py` — `WeChatDBReader` connects to the encrypted MsgStorage.db, loads group-name mappings from MicroMsg.db's Contact table, and polls the MSG table for new text messages. Copies the DB to temp when the live file is locked.

**Paste tools**: `paste.py` (local CLI, reads clipboard) and `streamlit_app.py` (web UI). Both use the same `TutorAssistantCore` pipeline. Same `TutorAssistantCore` pipeline. Deploy for free on Streamlit Community Cloud (https://share.streamlit.io) — push to GitHub, select repo, done. Secrets managed via Streamlit dashboard. Has manual push button for jobs that didn't auto-match.

**Parsing** is two-tier in `parser/parser.py`: `UnifiedParser` (regex rules) runs first, `AIParser` (DeepSeek API) falls back when regex yields nothing. `parse_multiple()` splits bulk text on separator patterns including teacher prefixes (Axxx:), message ID prefixes (WY杭州, 杭州ZN, 欢杭wy), markers (📌🌟♻️), hash tags (#新单, #加急), and numbered entries.

**Domain model**: `TutorJob` dataclass (`parser/tutor_job.py`). `is_valid()` requires both `address` and `salary`.

**Geo** (`geo/`): Amap APIs — `Geocoder` (address → coords), `DistanceCalculator` (route duration/distance per travel mode).

## Key details

- `DistanceCalculator.MODE_MAP` maps Chinese labels (电动自行车/驾车/骑行/步行) to Amap route modes.
- `Matcher._check_salary()` uses `salary_max` (upper bound) when present to compare against `min_salary`.
- `TutorJob.is_valid()` requires both address AND salary; jobs missing either are discarded.
- The DB polling approach requires WeChat to be running and `sqlcipher3` installed. If `sqlcipher3` fails to build on Python 3.14, use a Python 3.12 venv.
- `config.json` fields must match `UserConfig` dataclass in `config.py` exactly.
