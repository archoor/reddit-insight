# Reddit Insight

从 Reddit 社区讨论中发现商业机会的 AI 驱动分析系统。

## 系统概述

Reddit Insight 持续采集 Reddit 帖子和评论，利用 LLM 进行多维度商业洞见分析，最终为产品开发者和创业者提供经过验证的商业机会列表，包含：

- **真实痛点分析**：提取用户真实抱怨和未被满足的需求
- **付费意愿预测**：识别付费信号，估算价格敏感度
- **技术可行性评估**：评估 MVP 复杂度、技术栈建议和开发周期
- **竞品分析**：找出现有解决方案的弱点和市场空白
- **长期可持续性**：评估用户留存风险和运营挑战
- **商机综合评分**：0-100 分的综合商业机会得分（**每帖最多5个商机**）

---

## 系统架构

```
reddit-insight/
├── data-service/       # 统一后端服务 (Port 8001)
│   └── app/
│       ├── models/         # Subreddit / Post / Comment / CollectTask / PostAnalysis / Opportunity
│       ├── api/            # posts / tasks / subreddits / stats / analysis / opportunities / reports
│       ├── prompts/        # 六维度 LLM Prompt 模板（多商机输出）
│       └── services/
│           ├── collector.py        # Apify 帖子+评论一体化采集
│           ├── comment_fetcher.py  # 逐帖评论补采（备用）
│           ├── scheduler.py        # APScheduler 定时调度
│           ├── comment_sampler.py  # 四层智能采样
│           ├── token_budget.py     # Token 预算管理
│           ├── analyzer.py         # LLM 分析调度（一帖多商机）
│           └── opportunity_engine.py # 商机批量生成引擎
│
└── frontend/           # Next.js App Router (Port 3000)
    ├── app/
    │   ├── [locale]/                         # 国际化路由（默认 en，无前缀）
    │   │   ├── page.tsx                    # 首页（SEO优化）
    │   │   ├── opportunities/              # 商机列表 + 详情
    │   │   ├── insights/subreddit/[name]/[slug]/  # 帖子洞见详情（SEO核心页）
    │   │   └── admin/                      # 管理后台（noindex）
    │   ├── layout.tsx                      # 根布局（透传子树，见 [locale]/layout）
    │   └── globals.css                     # 全局样式（由 [locale]/layout 引入）
    ├── i18n/                               # next-intl：routing / request / navigation
    ├── messages/                         # 文案：en.json + 各语言覆盖（deepmerge）
    ├── middleware.ts                       # 语言检测与路由
    ├── components/
    │   ├── admin/
    │   │   ├── dashboard.tsx       # 后台入口：Tab 路由 + Toast 全局通知
    │   │   ├── overview-tab.tsx    # 总览：指标卡 + 状态分布 + 快捷操作
    │   │   ├── channels-tab.tsx    # 频道管理：增删改查 + 采集参数配置
    │   │   ├── tasks-tab.tsx       # 采集任务：创建/运行/调度 + 自动轮询
    │   │   └── posts-tab.tsx       # 帖子浏览：多维筛选 + 分页 + 触发分析
    │   └── ui/
    │       ├── modal.tsx / button.tsx / card.tsx / badge.tsx
    └── lib/
        ├── api.ts                  # Data / Insight API 封装
        ├── locale-path.ts          # 带语言前缀的绝对 URL（JSON-LD 等）
        └── utils.ts
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 数据采集 | Apify `fatihtahta/reddit-scraper-search-fast` |
| 后端框架 | FastAPI + SQLModel |
| 数据库 | SQLite（开发）→ PostgreSQL（生产） |
| 任务调度 | APScheduler |
| LLM 集成 | LiteLLM（支持 OpenAI / Claude / DeepSeek / Gemini） |
| Token 管理 | tiktoken |
| 前端框架 | Next.js App Router |
| UI 组件 | shadcn/ui + TailwindCSS |
| 国际化 | next-intl（**仅界面文案**；Reddit 帖子/评论/LLM 原文不翻译） |
| SEO | next-sitemap + next/metadata + JSON-LD |

---

## 快速开始

### 1. 环境准备

**要求：**
- Python 3.11+（使用 uv 管理）
- Node.js 18+（使用 npm 管理）
- Apify 账号和 API Token
- OpenAI / Claude / DeepSeek 任一 LLM API Key

### 2. 后端服务（data-service）

```bash
cd data-service

# 配置环境变量（填入 APIFY_API_TOKEN 和 LLM_API_KEY）
# .env 文件已存在，直接编辑即可

# 安装依赖（首次运行）
uv sync

# 如果有旧数据库，先执行迁移脚本
uv run python scripts/migrate_insight.py

# 启动服务（Port 8001）
uv run python -m app.main
```

**验证：** 访问 http://localhost:8001/docs 查看完整 API 文档

### 3. Frontend（前端）

```bash
cd frontend

# 配置环境变量
cp .env.local.example .env.local
# .env.local 只需配置一个变量：NEXT_PUBLIC_API_URL=http://localhost:8001

# 安装依赖
npm install

# 开发模式启动（Port 3000）
npm run dev
```

**界面语言（10 种）：** 默认 `en`；另有 `es`、`pt-BR`、`fr`、`de`、`ja`、`ko`、`ar`、`zh-Hans`、`zh-Hant`（繁体中文，列表最后一项）。导航栏右侧可选择语言。默认语言 URL **不带** 前缀（如 `/opportunities`），其他语言带前缀（如 `/zh-Hans/opportunities`、`/zh-Hant/opportunities`）。文案位于 `frontend/messages/`：`en.json` 为完整基准，其余文件通过 `deepmerge` 覆盖翻译。

---

## 使用流程

### Step 1：添加要监控的 Subreddit

```bash
curl -X POST http://localhost:8001/api/subreddits \
  -H "Content-Type: application/json" \
  -d '{"name": "SaaS", "display_name": "SaaS"}'
```

### Step 2：创建并运行采集任务

```bash
# 创建任务
curl -X POST http://localhost:8001/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"subreddit_name": "SaaS", "sort_by": "hot", "post_limit": 25, "fetch_comments": true}'

# 手动触发（任务 ID 为 1）
curl -X POST http://localhost:8001/api/tasks/1/run
```

### Step 3：触发 LLM 分析

```bash
# 批量分析未处理的帖子（最多20篇，并发3个）
curl -X POST "http://localhost:8001/api/analysis/trigger-batch?max_posts=20"
```

**分析状态说明：**

| 状态 | 含义 | 前端展示 |
|------|------|----------|
| `pending` | 待分析 | 灰色"待分析" |
| `analyzing` | 分析进行中 | 🔄 动画"分析中..." |
| `done` | 分析完成 | ✅ 绿色"已完成" |
| `failed` | 分析失败 | ❌ 红色"失败" |
| `skipped` | 评论不足跳过 | 灰色"已跳过" |

### Step 4：查看商机

访问 http://localhost:3000/opportunities 查看所有商机排行。

每篇帖子最多可产出 **5个商机**，由 LLM 根据讨论内容自动判断数量。

---

## 核心 API 参考

所有接口统一在 **Port 8001**，访问 http://localhost:8001/docs 查看交互式文档。

### 数据采集

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST/PATCH/DELETE | `/api/subreddits/*` | 频道管理 |
| GET | `/api/posts` | 帖子列表（支持分页/筛选） |
| GET/POST/DELETE/PATCH | `/api/tasks/*` | 采集任务管理 |
| GET | `/api/stats/overview` | 统计概览 |

### LLM 分析

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/analysis/trigger/{post_id}` | 触发单帖分析 |
| POST | `/api/analysis/re-analyze/{post_id}` | 强制重新分析 |
| POST | `/api/analysis/trigger-batch` | 批量触发分析 |
| GET | `/api/analysis/{post_id}` | 获取分析结果（含 opportunities_raw 数组） |
| GET | `/api/analysis` | 分析结果列表 |

### 商机

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/opportunities` | 商机列表（支持 post_id / subreddit / recommendation 筛选） |
| GET | `/api/opportunities/top` | Top N 商机 |
| GET | `/api/opportunities/{id}` | 商机详情（含来源帖子信息） |
| GET | `/api/opportunities/by-slug/{slug}` | 通过 slug 获取（SEO 用） |
| GET | `/api/reports/overview` | 整体报告 |
| GET | `/api/reports/subreddit/{name}` | 版块报告 |

---

## LLM 配置

在 `data-service/.env` 中配置：

```bash
# OpenAI（推荐 gpt-4o-mini 性价比高）
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-...

# Claude（分析质量更高）
# LLM_MODEL=claude-3-haiku-20240307
# LLM_API_KEY=sk-ant-...

# DeepSeek（国内可用，成本极低）
# LLM_MODEL=deepseek/deepseek-chat
# LLM_API_KEY=sk-...
# LLM_API_BASE=https://api.deepseek.com

# Gemini（免费额度高）
# LLM_MODEL=gemini/gemini-2.0-flash
# LLM_API_KEY=AIza...
```

---

## 数据模型

### 商机（Opportunity）关系

```
Post (1) ──── (1) PostAnalysis
  │                    │
  └──── (1:N) ──── Opportunity[]   ← 最多5条，每条独立评分
                        ↑
              通过 post_id + opportunity_index 唯一标识
```

### 分析状态流转

```
pending → [触发分析] → analyzing → done
                              ↘ failed
                              ↘ skipped（评论 < 3 条）
```

---

## 评论智能采样策略

当帖子评论数量大时，系统采用四层策略确保 LLM 分析质量：

1. **预过滤**：去除已删除、太短（<15字符）、低分（<-2分）的评论
2. **多维度采样**：高赞(30%) + 长文(20%) + 一级回复(20%) + 社区认可(15%) + 随机(15%)
3. **动态分批**：基于 tiktoken 精确计算 token，超出预算则分批处理
4. **批次合并**：多批 LLM 结果智能合并，消除重复痛点

---

## 数据库迁移

如果有旧版数据库（来自 v1.x），执行以下迁移脚本：

```bash
cd data-service
# 迁移 post_analysis 和 opportunity 表结构
uv run python scripts/migrate_insight.py

# 迁移 collect_task 和 subreddit 表（旧版已执行则跳过）
uv run python scripts/migrate_db.py
```

---

## 成本参考

| 项目 | 单价 | 月均 |
|------|------|------|
| Apify（帖子+评论采集） | $1.5/1K条 | ~$8-20 |
| GPT-4o-mini（分析） | ~$0.01-0.05/帖 | ~$5-20 |
| DeepSeek Chat（替代） | ~$0.001/帖 | <$2 |

---

## 项目状态

**已完成：**
- ✅ 数据采集：Apify 帖子+评论一体化采集 + REST API + APScheduler
- ✅ LLM 分析：六维度分析 + **一帖多商机**（最多5个）+ 分析状态实时追踪
- ✅ 商机评估：商机批量生成 + 多维度评分 + 版块/全局报告
- ✅ 前端：管理后台(/admin) + SEO 前台 + 商机展示页
- ✅ 服务合并：data-service + insight-service 统一为单一后端
- ✅ 数据库迁移脚本（旧数据无损迁移）
- ✅ Bug 修复：JOIN 自关联、线程池无限制、sys.path hack

**待优化：**
- [ ] 跨帖商机聚合（同一痛点跨多帖合并）
- [ ] 邮件通知（高分商机提醒）
- [ ] PostgreSQL 生产环境迁移
- [ ] Docker Compose 一键部署
