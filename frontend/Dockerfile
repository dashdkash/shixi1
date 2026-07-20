# ═══════════════════════════════════════════════════════
# 前端多阶段构建 — Node 构建 + Nginx 运行
# 最终镜像约 ~20MB
# ═══════════════════════════════════════════════════════

# ── 阶段 1：构建 ──────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# 先拷贝依赖清单，利用 Docker 缓存层
COPY package.json ./
RUN npm install

# 拷贝源码并构建
COPY . .
RUN npm run build

# ── 阶段 2：运行 ──────────────────────────────────────
FROM nginx:alpine

# 移除 Nginx 默认配置
RUN rm -rf /etc/nginx/conf.d/*

# 拷贝自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 从构建阶段拷贝产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
