# OA 公文助手前端管理台

## 1. 安装依赖

```bash
npm install
```

## 2. 配置 API 地址

```bash
copy .env.example .env
```

默认后端地址为 `http://localhost:8080`。

## 3. 启动开发环境

```bash
npm run dev
```

浏览器访问 `http://localhost:5173`。

## Docker 启动（Nginx 静态托管）

在项目根目录执行：

```bash
docker compose up -d --build frontend
```

访问地址：

- `http://localhost:5173`

## 功能

- 上传模板（支持 `docx` / `txt` / `md`）
- 查看模板列表和模板解析结果
- 创建校对任务（可绑定模板）
- 查询任务状态和结果
