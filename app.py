# app.py
from flask import Flask, request, jsonify, render_template
import requests
from bs4 import BeautifulSoup
import re
import time

app = Flask(__name__)

# ---- 新增/调整：会话、URL、请求头 ----
S = requests.Session()  # 维持 Cookie 的会话
BASE_URL_TMPL = "https://www.chemicalbook.com/CAS_{cas}.htm"
SEARCH_URL_TMPL = "https://www.chemicalbook.com/Search.aspx?keyword={q}&searchflag=CAS"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# ---- 原有配置 ----
_CACHE = {}            # 简单内存缓存
TTL_SECONDS = 6 * 3600 # 缓存 6 小时
SECTION_ANCHOR = "物理化学性质"
CAS_PATTERN = re.compile(r"^\s*\d{2,7}-\d{2}-\d\s*$")

FIELD_ALIASES = {
    "熔点": ["熔点", "Melting point", "Melting Point"],
    "沸点": ["沸点", "Boiling point", "Boiling Point"],
    "密度": ["密度", "Density"],
    "闪点": ["闪点", "Flash point", "Flash Point"],
    "折射率": ["折射率", "Refractive index", "Refractive Index"],
    "蒸气压": ["蒸气压", "Vapor pressure", "Vapour pressure"],
    "蒸气密度": ["蒸气密度", "Vapor density", "Vapour density"],
    "pKa": ["酸度系数", "酸度系数(pKa)", "pKa"],
    "储存条件": ["储存条件", "Storage conditions", "Storage Condition"],
    "溶解度": ["溶解度", "Solubility"],
    "自燃温度": ["自燃温度", "Autoignition temperature", "Auto-ignition temperature"],
}

# ---- 新增：预热 Cookie ----
def _prime_cookies():
    try:
        S.get("https://www.chemicalbook.com/ProductIndex.aspx",
              headers=HEADERS, timeout=15)
    except Exception:
        pass  # 失败也不致命

# ---- 新增：从搜索页解析详情链接 ----
def _resolve_detail_url_from_search(cas: str) -> str | None:
    url = SEARCH_URL_TMPL.format(q=cas)
    r = S.get(url, headers={**HEADERS, "Referer": "https://www.chemicalbook.com/"},
              timeout=20)
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    # 目标优先：/CAS_<cas>.htm
    link = soup.select_one(f'a[href*="/CAS_{cas}.htm"]')
    if link and link.get("href"):
        href = link["href"]
        return "https://www.chemicalbook.com" + href if href.startswith("/") else href
    # 兜底：产品属性页
    for a in soup.select("a[href]"):
        href = a["href"]
        if "ChemicalProductProperty" in href or "ProductChemicalProperties" in href:
            return "https://www.chemicalbook.com" + href if href.startswith("/") else href
    return None

# ---- 替换：带 Referer 的重试抓取 ----
def _get_html(url: str, referer: str | None = None) -> str:
    now = time.time()
    if url in _CACHE and now - _CACHE[url]["t"] < TTL_SECONDS:
        return _CACHE[url]["html"]

    headers = HEADERS.copy()
    if referer:
        headers["Referer"] = referer

    last = None
    for attempt in range(4):  # 退避重试：1.5s, 3.0s, 4.5s
        r = S.get(url, headers=headers, timeout=20)
        last = r
        if r.status_code == 200 and r.text:
            html = r.text
            _CACHE[url] = {"t": time.time(), "html": html}
            return html
        if r.status_code in (429, 503):
            time.sleep(1.5 * (attempt + 1))
            continue
        break
    raise RuntimeError(f"HTTP {last.status_code if last else '??'}")

# ---- 不变：解析属性 ----
def _extract_properties(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    full_text = soup.get_text("\n", strip=True)

    section_text = full_text
    m = re.search(SECTION_ANCHOR + r"(.*?)(?:\n##\s|\Z)", full_text, flags=re.S)
    if m:
        section_text = m.group(1)

    def find_value(text: str, aliases: list[str]) -> str | None:
        pattern = r"(?:%s)\s*[:：]?\s*([^\n\r]+)" % "|".join(map(re.escape, aliases))
        mm = re.search(pattern, text, flags=re.I)
        if not mm:
            mm = re.search(pattern, full_text, flags=re.I)
        return mm.group(1).strip() if mm else None

    data = {}
    for key, aliases in FIELD_ALIASES.items():
        val = find_value(section_text, aliases)
        if val:
            data[key] = re.sub(r"\s+", " ", val).replace(" ,", ",").strip()

    cn_name = None
    m_cn = re.search(r"中文名称\s*([^\n]+)", full_text)
    if m_cn:
        cn_name = m_cn.group(1).strip()

    en_name = None
    m_en = re.search(r"英文名称\s*([^\n]+)", full_text)
    if m_en:
        en_name = m_en.group(1).strip()

    cas_in_page = None
    m_cas = re.search(r"\bCAS\s*[:：]?\s*([0-9\-]+)", full_text)
    if m_cas:
        cas_in_page = m_cas.group(1).strip()

    return {
        "meta": {"中文名称": cn_name, "英文名称": en_name, "CAS": cas_in_page},
        "properties": data,
    }

# ---- 路由 ----
@app.route("/")
def index():
    return render_template("index.html")

@app.get("/api/properties")
def api_properties():
    cas = (request.args.get("cas") or "").strip()
    if not cas:
        return jsonify({"ok": False, "error": "请提供 ?cas= 参数"}), 400
    if not CAS_PATTERN.match(cas):
        return jsonify({"ok": False, "error": "CAS 号格式看起来不对（应形如 67-56-1）"}), 400

    # 1) 预热 Cookie
    _prime_cookies()

    # 2) 先试直达
    direct_url = BASE_URL_TMPL.format(cas=cas)
    try:
        html = _get_html(direct_url, referer="https://www.chemicalbook.com/")
        payload = _extract_properties(html)
        return jsonify({
            "ok": True,
            "source_url": direct_url,
            "meta": payload.get("meta"),
            "properties": payload.get("properties") or {},
        })
    except Exception:
        # 3) 直达失败 → 走搜索页解析详情链接
        try:
            resolved = _resolve_detail_url_from_search(cas)
            if not resolved:
                raise RuntimeError("未从搜索页找到详情链接")
            html = _get_html(resolved, referer=SEARCH_URL_TMPL.format(q=cas))
            payload = _extract_properties(html)
            return jsonify({
                "ok": True,
                "source_url": resolved,
                "meta": payload.get("meta"),
                "properties": payload.get("properties") or {},
            })
        except Exception as e2:
            return jsonify({
                "ok": False,
                "error": f"抓取失败：{e2}",
                "source_url": direct_url
            }), 502

if __name__ == "__main__":
    # pip install flask requests beautifulsoup4 lxml
    app.run(host="0.0.0.0", port=8000, debug=True)
