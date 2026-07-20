## 新用户初始化步骤

### 1. 启动基础设施（Docker）
```bash
cd Internship_Summer_2026
docker-compose up -d
```
这会启动 PostgreSQL(pgvector)、Redis、MinIO。

### 2. 执行数据库迁移（建表）
```bash
cd backend
alembic upgrade head
```
抱歉数据库版本删掉了...
首先请删掉alembic下除了我的版本以外的version

清除pycache
1. 确保 pgvector 扩展已安装（在新数据库中）
docker exec -it rsod-postgres psql -U lujie -d lujie -c "CREATE EXTENSION IF NOT EXISTS vector;"
2. 清除旧的 alembic 版本记录，让 alembic 认为数据库是全新的
docker exec -it rsod-postgres psql -U lujie -d lujie -c "DROP TABLE IF EXISTS alembic_version;"
3. 清理 __pycache__ 防止缓存干扰
Remove-Item -Recurse -Force alembic\versions\__pycache__ -ErrorAction SilentlyContinue
4. 执行迁移
python -m alembic upgrade head

不知道这个方法行不行


### 3. 初始化角色（必须）
```bash
cd backend
python init_roles.py
```
创建 `admin`（管理员）和 `user`（普通用户）两个系统角色。

### 4. 初始化检测场景（必须）
```bash
cd backend
python tools/init_scenes.py
```
创建 4 个检测场景：
- `weeds`（农田杂草识别，15 种杂草 + 中文名映射）
- `remote_sensing`（遥感目标检测）
- `traffic`（交通目标检测）
- `general`（COCO 通用目标检测，80 类）

### 5. 导入知识库文档（推荐）
```bash
cd backend
python add_knowledge.py "防治手册.md"
```
将防治手册导入 RAG 知识库，Agent 才能回答防治建议类问题。

### 6. 放置检测模型（必须）
确保 `models/us_weeds_v3.0.0/` 下有训练好的权重文件（`best.pt`），以及根目录下的 `yolo11n.pt`（预训练模型，用于训练功能）。

或者你可以设置设置settings.py : DEFAULT_MODEL_PATH: str = "models/us_weeds_v3.0.0/best.pt" （到自己的模型目录）

检测模型选择我使用了这个setting的地址作为第一优先级，可以增加检测模型选择功能

### 7. 配置环境变量
复制 `.env.example` 为 `.env`，填入 API Key、数据库连接等配置。

好吧其实我还没有同步，不知道`.env.example`对不对...你们看着配，等我改
