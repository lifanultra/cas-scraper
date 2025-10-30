

# CAS 物化性质查询（ChemicalBook）

一个极简的 Web 应用：输入化学物质 **CAS** 号，抓取 **ChemicalBook** 的页面并解析常见物化性质。前端用 **HTML/CSS/JavaScript**，后端用 **Python + Flask**。

> ⚠️ 本项目仅用于学习与检索演示。请遵守目标网站的服务条款与 robots 协议，控制抓取频率，勿用于批量采集或商业用途。

## ✨ 能做什么

- 输入 **CAS 号**（如 `67-56-1`、`7732-18-5`），自动定位对应详情页并解析常见性质。

- 页面**仅展示 4 个字段**（中英双语标签）：

  - 熔点 / Melting point
  - 沸点 / Boiling point
  - 溶解度 / Solubility
  - 储存条件 / Storage conditions

- 具备简易**反爬处理**：

  - 先访问主页“预热 Cookie” → 走**搜索页** → 携带 **Referer** 再访问详情页
  - 会话维持（`requests.Session`）+ 简单**退避重试**（对 429/503）

  ## 🧱 项目结构

  ```markdown
  cas-scraper/
  ├─ app.py                  # Flask 后端（抓取、解析、API）
  ├─ templates/
  │  └─ index.html           # 前端页面（双语表头）
  └─ static/
     ├─ styles.css           # 样式
     └─ app.js               # 前端逻辑（仅渲染四个字段，双语标签）
  ```

## ⚙️ 环境要求

- Python 3.9+（Windows / macOS / Linux 均可）
- 依赖：`Flask`, `requests`, `beautifulsoup4`, `lxml`

可选（生产部署）：

- Linux 服务器（推荐）
- `gunicorn`（或 Windows 下用 `waitress`）
- 反向代理（Nginx 等）

## 🚀 本地运行（开发）

```markdown
# 1) 进入项目根目录
cd cas-scraper

# 2) （可选）创建虚拟环境
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
# .\.venv\Scripts\Activate.ps1

# 3) 安装依赖
pip install -U pip
pip install flask requests beautifulsoup4 lxml

# 4) 启动
python app.py
```

打开浏览器访问：`http://127.0.0.1:8000`

**提示：** 首次请求若触发 503，可稍等数秒再次查询或换个网络。代码已包含退避重试与搜索页兜底流程。

## 🧩 配置项（按需）

在 `app.py` 里可调整：

- `TTL_SECONDS`：页面缓存时间（默认 6 小时）
- `ALLOWED_FIELDS = ["熔点","沸点","溶解度","储存条件"]`：接口返回字段白名单
- `HEADERS`：请求头（如需模拟不同 UA）
- 反爬流程：`_prime_cookies()` / `_resolve_detail_url_from_search()` / `_get_html()`（带 Referer 的退避重试）

在 `static/app.js` 里可调整前端显示顺序/标签：

```markdown
const order = ["熔点","沸点","溶解度","储存条件"];
const labelMap = {
  "熔点": "熔点 / Melting point",
  "沸点": "沸点 / Boiling point",
  "溶解度": "溶解度 / Solubility",
  "储存条件": "储存条件 / Storage conditions",
};
```

## 🔌 API

### `GET /api/properties?cas=<CAS号>`

**示例：**
 `/api/properties?cas=7732-18-5`

**成功响应：**

```
{
  "ok": true,
  "source_url": "https://www.chemicalbook.com/CAS_7732-18-5.htm",
  "meta": {
    "中文名称": "水",
    "英文名称": "Water",
    "CAS": "7732-18-5"
  },
  "properties": {
    "熔点": "0 °C",
    "沸点": "100 °C",
    "溶解度": "—",
    "储存条件": "2-8 °C"
  }
}
```

**失败响应：**

```markdown
{ "ok": false, "error": "抓取失败：HTTP 503", "source_url": "..." }
```

## 🛡️ 生产部署指南

### 方案 A：Gunicorn（Linux 推荐）

1. 安装依赖：

```
pip install gunicorn gevent
```

1. 启动（示例：2 个 worker，4 线程）：

```
gunicorn app:app -b 0.0.0.0:8000 --workers 2 --threads 4 --timeout 60
```

1. 配置 Nginx（可选，HTTPS/反向代理/限速）：

```
server {
  listen 80;
  server_name your-domain.example;

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }

  # 静态资源可直接由 Flask 提供，或改为 Nginx 本地路径
}
```

> 生产环境请务必加上 HTTPS（Let’s Encrypt / ZeroSSL）与基本限流规则。

### 方案 B：Windows（Waitress）

```
pip install waitress
waitress-serve --host=0.0.0.0 --port=8000 app:app
```

### 方案 C：Docker（可选）

1. 新建 `requirements.txt`：

```
Flask
requests
beautifulsoup4
lxml
gunicorn
```

1. 新建 `Dockerfile`：

```
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PORT=8000
EXPOSE 8000

# 生产 WSGI：gunicorn
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "60"]
```

1. 构建 & 运行：

```
docker build -t cas-scraper .
docker run --rm -p 8000:8000 cas-scraper
```

> 将镜像推到你的仓库后，可在 Render / Railway / Fly.io 等平台直接部署。

## ❓常见问题（FAQ）

- **返回 `HTTP 503`？**
   ChemicalBook 的风控/防护导致。项目已实现：会话维持 + 主页预热 + 走搜索页 + Referer + 退避重试。仍偶发时：
  - 换个网络（热点/家庭宽带）；
  - 降低频率、提高缓存时间；
  - 适当调整 `User-Agent`。
- **字段为空/不完整？**
   不同条目的字段布局可能差异较大。解析逻辑优先在“物理化学性质”段落查找，找不到会全文兜底。你可在 `FIELD_ALIASES` 里补充别名。
- **想显示更多字段？**
  - 前端：改 `static/app.js` 的 `order` 与 `labelMap`；
  - 后端：改 `ALLOWED_FIELDS`（或去掉过滤）。
- **Windows 生产部署可以用 Gunicorn 吗？**
   不建议。Windows 下用 `waitress` 更稳；生产建议 Linux + Gunicorn。

------

## 🔒 合规与免责声明

- 请遵守目标站点 **Terms of Service** 与 **robots** 限制，控制抓取频率；
- 仅用于学习/研究，不对数据的准确性与时效性提供任何保证；
- 如需长期/高并发使用，请联系数据源平台获取正式 API 或授权。

------

## 🗺️ 路线图

- 多数据源兜底（如 PubChem、NIST 等官方/公开来源）
- 单位与数值清洗（统一 ℃ / K、去除 “(lit.)” 等标注）
- 多数据类型查询（如：苯乙烯等中文名称）
- 简单本地持久化（SQLite）与查询统计

------

## 📄 License

 **MIT License**