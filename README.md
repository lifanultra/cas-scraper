

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

# 常驻运行（systemd + Gunicorn）速查表

> 场景：把你的 Flask 应用（项目目录：`/www/wwwroot/chem.lifan.icu`，入口 `app.py` 内含 `app = Flask(__name__)`）以 **systemd 服务**常驻运行，并由 **Nginx** 反向代理到域名。

------

## 一次性准备（在服务器终端执行）

```
# 进入项目并创建虚拟环境
PROJECT=/www/wwwroot/chem.lifan.icu
VENVDIR=$PROJECT/.venv

cd $PROJECT
python3 -m venv $VENVDIR
source $VENVDIR/bin/activate
pip install -U pip
pip install gunicorn flask requests beautifulsoup4 lxml

# 准备日志目录
sudo mkdir -p /var/log/chem-scraper
sudo chown -R $USER:$USER /var/log/chem-scraper
```

------

## systemd 服务文件示例

> 文件路径：`/etc/systemd/system/chem-scraper.service`

```
[Unit]
Description=CAS Scraper (Gunicorn)
After=network.target

[Service]
User=root
WorkingDirectory=/www/wwwroot/chem.lifan.icu
Environment="PATH=/www/wwwroot/chem.lifan.icu/.venv/bin"
# 生产建议只监听本机，再由 Nginx 反代
ExecStart=/www/wwwroot/chem.lifan.icu/.venv/bin/gunicorn app:app \
  -b 127.0.0.1:8000 --workers 2 --threads 4 --timeout 60 \
  --access-logfile /var/log/chem-scraper/access.log \
  --error-logfile  /var/log/chem-scraper/error.log
# 可选：优雅热重载（给 master 进程发 HUP 信号）
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

应用/更新服务文件后：

```
sudo systemctl daemon-reload          # 让 systemd 重新读取服务文件
sudo systemctl enable --now chem-scraper   # 开机自启并立即启动
```

------

## 常用管理命令（背下来就行）

```
# 启动 / 停止 / 重启
sudo systemctl start chem-scraper
sudo systemctl stop chem-scraper
sudo systemctl restart chem-scraper          # 改了代码后常用

# （若定义了 ExecReload）优雅重载 Gunicorn
sudo systemctl reload chem-scraper

# 查看状态
sudo systemctl status chem-scraper           # q 退出
systemctl is-active chem-scraper             # active/inactive
systemctl is-enabled chem-scraper            # enabled/disabled

# 服务文件有修改后
sudo systemctl daemon-reload
sudo systemctl restart chem-scraper

# 查看日志（journalctl）
sudo journalctl -u chem-scraper -f           # 实时滚动（Ctrl+C 退出）
sudo journalctl -u chem-scraper -n 200       # 最近 200 行
sudo journalctl -u chem-scraper --since "10 min ago"
sudo journalctl -u chem-scraper -b           # 本次开机日志
```

------

## 典型操作流程

- **更新代码** → `sudo systemctl restart chem-scraper`

- **改了服务文件（.service）** → `sudo systemctl daemon-reload && sudo systemctl restart chem-scraper`

- **切换端口**（例如 8000 → 9000）
   1）改 `.service` 中的 `-b 127.0.0.1:9000` → `daemon-reload` → `restart`
   2）同步修改 Nginx 的 `proxy_pass` → `sudo nginx -t && sudo systemctl reload nginx`

- **查看监听端口** → `sudo ss -tlnp | grep gunicorn` 或 `grep 8000`

- **放行 80/443（如启用 UFW）**

  ```
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  ```

------

## Nginx 反向代理（示例片段）

```
# HTTP 80：跳转到 HTTPS（可选）
server {
  listen 80;
  server_name chem.lifan.icu;
  return 301 https://chem.lifan.icu$request_uri;
}

# HTTPS 443
server {
  listen 443 ssl http2;
  server_name chem.lifan.icu;

  ssl_certificate     /etc/letsencrypt/live/chem.lifan.icu/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/chem.lifan.icu/privkey.pem;

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;
    proxy_read_timeout 60s;
    proxy_send_timeout 60s;
  }

  # 可选：直接由 Nginx 提供静态资源
  location /static/ {
    alias /www/wwwroot/chem.lifan.icu/static/;
    access_log off;
    expires 7d;
    add_header Cache-Control "public, max-age=604800, immutable";
  }
}
```

测试并重载：

```
sudo nginx -t && sudo systemctl reload nginx
```

------

## 故障排查速查

- **`ModuleNotFoundError: No module named 'app'`**
   `WorkingDirectory` 不对或入口不是 `app.py`。确保 `/www/wwwroot/chem.lifan.icu/app.py` 存在且有 `app = Flask(__name__)`。若入口叫 `server.py`，把 `app:app` 改为 `server:app`。
- **端口占用 / 无法连接**
   `sudo ss -tlnp | grep 8000` 查占用；改端口或停止冲突进程。
- **依赖缺失**
   确认用的是 **同一个 venv**：`/www/wwwroot/chem.lifan.icu/.venv/bin/gunicorn`
   需要时在 venv 里重新：`pip install -U -r requirements.txt`
- **Nginx 502**
   大概率是 Gunicorn 没起来或监听地址不匹配；`systemctl status chem-scraper` & `journalctl -u chem-scraper -n 200` 对照排查。
- **改了 .service 不生效**
   记得 `sudo systemctl daemon-reload` 再 `restart`。

------

## 备选后台方案（不建议用于生产）

```
# 守护进程模式（Gunicorn 自带）
/www/wwwroot/chem.lifan.icu/.venv/bin/gunicorn --chdir /www/wwwroot/chem.lifan.icu app:app \
  -b 0.0.0.0:8000 --workers 2 --threads 4 --timeout 60 \
  -D --pid /run/chem-scraper.pid \
  --access-logfile /var/log/chem-scraper/access.log \
  --error-logfile  /var/log/chem-scraper/error.log

# 停止
kill "$(cat /run/chem-scraper.pid)"
```

或用 `screen`/`tmux` 保活会话（开发调试方便，生产不推荐）。

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