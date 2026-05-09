# 家教信息自动筛选系统

自动监听微信家教群消息，筛选符合条件的家教信息并推送到手机。

## 功能

- 自动解析微信家教群消息
- 按薪资、科目、年级、通勤距离筛选
- 区域过滤（跳过偏远地区）
- 骑行时间计算
- Bark 推送通知

## 安装

```bash
pip install -r requirements.txt
```

## 配置

修改 `config.json`：

```json
{
  "my_address": "你的出发点地址",
  "my_coords": [经度, 纬度],
  "min_salary": 120,
  "subjects": ["数学", "英语", "科学"],
  "grades": ["高一", "高二", "高三", "高中"],
  "max_commute_time": 35,
  "commute_mode": "电动自行车",
  "skip_districts": ["西湖区", "上城区"],
  "target_groups": ["群名1", "群名2"],
  "amap_key": "你的高德API Key",
  "deepseek_key": "你的DeepSeek Key（可选）",
  "bark_key": "你的Bark Key"
}
```

### 配置说明

| 字段 | 说明 |
|------|------|
| `my_address` | 出发点地址（用于计算通勤） |
| `my_coords` | 经纬度坐标，可不填会自动获取 |
| `min_salary` | 最低时薪要求（元/小时） |
| `subjects` | 你能教的科目 |
| `grades` | 你能教的年级 |
| `max_commute_time` | 最大通勤时间（分钟） |
| `commute_mode` | 出行方式：电动自行车/骑行/步行/驾车 |
| `skip_districts` | 跳过的区域列表 |
| `target_groups` | 要监听的微信群名 |
| `amap_key` | 高德地图 Web API Key |
| `deepseek_key` | DeepSeek API Key（可选，用于AI解析兜底） |
| `bark_key` | Bark 推送 Key |

## 运行

### 测试模式（模拟消息）
```bash
python test_messages.py
```

### 监听模式（需要 ComWeChatRobot）
```bash
python main.py
```

## 依赖

- Python 3.10+
- 高德地图 Web API
- Bark（iOS推送）
- ComWeChatRobot（微信Hook，用于监听模式）

## 项目结构

```
├── core.py              # 核心逻辑
├── main.py              # 主程序入口
├── test_messages.py      # 测试脚本
├── config.py            # 配置加载
├── config.json          # 配置文件
├── filter.py            # 区域过滤
├── matcher.py           # 条件匹配
├── pusher.py           # 推送模块
├── parser/             # 消息解析
│   ├── parser.py
│   ├── unified_parser.py
│   ├── ai_parser.py
│   └── tutor_job.py
└── geo/                # 地理计算
    ├── geocoder.py
    └── distance.py
```
