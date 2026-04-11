# OA Word

后端是 FastAPI + RQ + PostgreSQL + Redis，前端是 Vite + React + Nginx。

当前项目已经具备：
- 管理口令保护
- Alembic 数据库迁移
- 规则管理、公私规则、模板规则
- LLM 结构化输出校验与重试
- 任务失败自动重试和人工重放
- 基础运维指标接口

## 快速启动

1. 复制配置文件。

```powershell
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env
```

2. 填写 `.env` 里的关键配置：
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `ADMIN_API_TOKEN`

3. 启动服务。

```powershell
docker compose up -d --build
```

## 访问地址

- 前端管理台: `http://localhost:5173`
- 后端 API: `http://localhost:8080`
- 健康检查: `http://localhost:8080/healthz`
- 运维指标: `http://localhost:8080/api/v1/ops/metrics`

## 首次部署说明

- `migrate` 服务会先执行 `alembic upgrade head`
- `api` 和 `worker` 会在迁移成功后启动
- 如果数据库里已经存在旧版本 `create_all` 建出来的表，当前基线迁移也能兼容

## 核心环境变量

### 基础

- `APP_ENV`: `dev` 或 `prod`
- `ADMIN_API_TOKEN`: 管理接口口令，`prod` 必填
- `CORS_ALLOW_ORIGINS`: 允许的前端来源，逗号分隔

### 数据库与队列

- `DATABASE_URL`
- `REDIS_URL`

### 大模型

- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `DEFAULT_TIMEOUT_SEC`

### 任务与边界控制

- `MAX_TASK_TEXT_CHARS`
- `MAX_TEMPLATE_FILE_BYTES`
- `MAX_TEMPLATE_TEXT_CHARS`
- `MAX_ISSUES_PER_TASK`
- `MAX_ACTIVE_TASKS`
- `SUBMIT_RATE_LIMIT_WINDOW_SEC`
- `SUBMIT_RATE_LIMIT_MAX_REQUESTS`
- `MAX_ERROR_MSG_CHARS`

### 失败恢复

- `TASK_MAX_RETRIES`
- `RETRYABLE_TASK_ERROR_TYPES`

## 运维检查

### 查看服务状态

```powershell
docker compose ps
```

### 查看迁移日志

```powershell
docker compose logs migrate --tail=200
```

### 查看 API 和 worker 日志

```powershell
docker compose logs api worker --tail=200
```

## 上线前必做

- 轮换真实 LLM API Key，不要继续使用开发阶段暴露过的密钥
- 将 `APP_ENV` 改为 `prod`
- 设置强口令 `ADMIN_API_TOKEN`
- 缩小 `CORS_ALLOW_ORIGINS`
- 做一次 `docker compose up -d --build` 的全链路验收
