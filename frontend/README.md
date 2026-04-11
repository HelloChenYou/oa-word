# OA Word Frontend

前端技术栈：
- Vite
- React
- TypeScript
- Nginx

## 本地开发

1. 安装依赖

```powershell
npm install
```

2. 复制环境变量

```powershell
Copy-Item .env.example .env
```

3. 启动开发服务器

```powershell
npm run dev
```

默认访问地址：
- `http://localhost:5173`

## Docker 运行

在项目根目录执行：

```powershell
docker compose up -d --build frontend
```

## 功能入口

当前管理台包含：
- 规则管理
- 模板管理
- 任务管理

如果后端启用了 `ADMIN_API_TOKEN`，需要在页面顶部填写管理口令后再访问受保护接口。
