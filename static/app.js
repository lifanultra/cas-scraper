const form = document.getElementById("query-form");
const casInput = document.getElementById("cas-input");
const loadingEl = document.getElementById("loading");
const resultEl = document.getElementById("result");
const errorEl = document.getElementById("error");
const metaEl = document.getElementById("meta");
const tbody = document.getElementById("props-body");
const sourceEl = document.getElementById("source");

const CAS_REGEX = /^\s*\d{2,7}-\d{2}-\d\s*$/;

function show(el) { el.hidden = false; }
function hide(el) { el.hidden = true; }
function clearChildren(el) { while (el.firstChild) el.removeChild(el.firstChild); }

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  hide(errorEl);
  hide(resultEl);
  show(loadingEl);

  const cas = casInput.value.trim();
  if (!CAS_REGEX.test(cas)) {
    hide(loadingEl);
    errorEl.textContent = "CAS 号格式看起来不对（应形如 67-56-1）";
    show(errorEl);
    return;
  }

  try {
    const res = await fetch(`/api/properties?cas=${encodeURIComponent(cas)}`);
    const data = await res.json();

    hide(loadingEl);

    if (!data.ok) {
      errorEl.textContent = data.error || "查询失败";
      show(errorEl);
      return;
    }

    // 元信息
    const metaBits = [];
    if (data.meta?.中文名称) metaBits.push(`中文名称：${data.meta.中文名称}`);
    if (data.meta?.英文名称) metaBits.push(`英文名称：${data.meta.英文名称}`);
    if (data.meta?.CAS)        metaBits.push(`CAS：${data.meta.CAS}`);
    metaEl.textContent = metaBits.join(" / ") || "";

    // 表格
    clearChildren(tbody);
    const props = data.properties || {};
// 仅显示这四项
// 只显示 4 个字段，并用中英双语标签
const order = ["熔点", "沸点", "溶解度", "储存条件"];
const labelMap = {
  "熔点": "熔点 / Melting point",
  "沸点": "沸点 / Boiling point",
  "储存条件": "储存条件 / Storage conditions",
};
const keys = order.filter(k => k in props); // 不再追加其它字段



    if (keys.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 2;
      td.textContent = "未从来源页面解析到常见物化性质。";
      tr.appendChild(td);
      tbody.appendChild(tr);
    } else {
      keys.forEach(k => {
        const tr = document.createElement("tr");
        const tdK = document.createElement("td");
        tdK.textContent = labelMap[k] || k;
        const tdV = document.createElement("td");
        tdV.textContent = props[k];
        tr.appendChild(tdK);
        tr.appendChild(tdV);
        tbody.appendChild(tr);
      });
    }

    sourceEl.innerHTML = `来源：<a href="${data.source_url}" target="_blank" rel="noopener">ChemicalBook 页面</a>`;
    show(resultEl);

  } catch (err) {
    hide(loadingEl);
    errorEl.textContent = "网络或服务器异常，请稍后重试。";
    show(errorEl);
  }
});
