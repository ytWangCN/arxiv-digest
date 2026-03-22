# arxiv-digest

自动追踪 arxiv 指定领域的最新论文，每个工作日推送日报（含大模型评分与中文摘要），每周日推送 AI 生成的周趋势分析报告，发送至 Gmail 邮箱。

## 功能

- **工作日日报**：抓取当日新论文 → 关键词过滤 → 大模型评分推荐 → 中文摘要 → 发送邮件
- **周日周报**：汇总过去一周论文 → AI 分析热点方向与新兴趋势 → 发送趋势报告
- **服务端过滤**：关键词直接嵌入 arxiv 查询，精准高效，不受论文总量限制
- **灵活配置**：关键词、分类、评分阈值、发送时间均在 `config.yaml` 中统一管理

## 目录结构

```
arxiv-digest/
├── config.yaml          # 所有配置（关键词、邮件、LLM、调度）
├── fetcher.py           # arxiv 论文抓取（服务端关键词 + 日期过滤）
├── recommender.py       # 大模型评分与中文摘要生成
├── trend_analyzer.py    # 每周趋势分析（AI 生成周报内容）
├── mailer.py            # HTML 邮件构建与 Gmail 发送
├── main.py              # 单次执行入口（日报流程）
├── scheduler.py         # 定时调度（工作日日报 / 周日周报）
└── requirements.txt
```

## 安装

```bash
cd arxiv-digest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置

编辑 `config.yaml`：

```yaml
arxiv:
  categories:         # arxiv 分类代码（cs.AI / cs.CV / cs.LG / cs.CL 等）
  keywords:           # 关键词，OR 逻辑，命中标题或摘要任意一个即保留
  max_results: 200    # 单次最大抓取量
  days_back: 1        # 抓取最近几天的论文（日常保持 1）

email:
  sender:             # Gmail 发件地址
  app_password:       # Gmail 应用专用密码（16位）
  recipients:         # 收件人列表

llm:
  api_key:            # API Key
  base_url:           # API 地址
  model:              # 模型名称

recommender:
  enabled: true
  interests:          # 你的研究兴趣描述，大模型据此打分
  score_threshold: 6  # 只推送评分 >= 该值的论文（1-10）
  concurrency: 3      # 并发请求数

scheduler:
  send_time: "08:00"  # 每日发送时间
  timezone: Asia/Shanghai
```

### Gmail 应用专用密码

1. 开启 Google 账号的**两步验证**
2. 进入 [安全设置](https://myaccount.google.com/security) → 搜索「应用专用密码」
3. 选择「邮件」生成 16 位密码，填入 `email.app_password`

### 支持的大模型

| 服务 | base_url | 模型示例 |
|------|----------|----------|
| Xiaomi Mimo | `https://api.xiaomimimo.com/v1` | `mimo-v2-flash` / `mimo-v2-pro` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 任意 OpenAI 兼容接口 | 自定义 | 自定义 |

## 运行

### 立即执行一次日报（测试）

```bash
.venv/bin/python main.py
```

### 立即生成并发送周报（测试）

```bash
.venv/bin/python -c "
from main import load_config
from trend_analyzer import analyze_weekly_trend
from mailer import send_trend_email
config = load_config()
send_trend_email(analyze_weekly_trend(config), config)
"
```

### 启动每日定时调度

```bash
.venv/bin/python scheduler.py
```

后台运行：

```bash
nohup .venv/bin/python scheduler.py > digest.log 2>&1 &
```

## 调度规则

| 日期 | 行为 |
|------|------|
| 周一至周五 | 推送当日论文日报（评分 + 中文摘要） |
| 周六 | 跳过（arxiv 无新论文） |
| 周日 | 发送过去一周趋势周报（AI 分析） |

## 邮件内容

**日报**：论文标题（可跳转）、作者、发布日期、分类标签、英文摘要节选、推荐理由、中文摘要、评分徽章（按分数高低排列）

**周报**：本周概览、热点研究方向（3-5个，含代表论文）、值得关注的论文、新兴趋势
