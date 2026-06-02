/* ============================================================
   OrbitGuard AI — frontend logic
   - Consome a API (API Gateway + Lambda). A URL é injetada no
     build via config.js (gerada pelo pipeline CI/CD a partir do
     output do Terraform). Se não existir, usa dados de demonstração.
   ============================================================ */

// No Azure Static Web Apps a API fica em /api (mesma origem, sem CORS).
// config.js pode sobrescrever para testes locais; senão usa /api.
const API_BASE_URL = window.ORBITGUARD_API || "/api";

/* ---------- Starfield ---------- */
(function starfield() {
  const c = document.getElementById("starfield");
  const ctx = c.getContext("2d");
  let stars = [];
  function resize() {
    c.width = window.innerWidth;
    c.height = window.innerHeight;
    stars = Array.from({ length: 140 }, () => ({
      x: Math.random() * c.width,
      y: Math.random() * c.height,
      r: Math.random() * 1.3 + 0.2,
      a: Math.random(),
      s: Math.random() * 0.02 + 0.003,
    }));
  }
  function draw() {
    ctx.clearRect(0, 0, c.width, c.height);
    for (const st of stars) {
      st.a += st.s;
      const tw = 0.4 + 0.6 * Math.abs(Math.sin(st.a));
      ctx.beginPath();
      ctx.arc(st.x, st.y, st.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(180,210,255,${tw})`;
      ctx.fill();
    }
    requestAnimationFrame(draw);
  }
  window.addEventListener("resize", resize);
  resize();
  draw();
})();

/* ---------- Animated counters ---------- */
(function counters() {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return;
      const el = e.target;
      const target = +el.dataset.count;
      let n = 0;
      const step = Math.max(1, Math.round(target / 40));
      const t = setInterval(() => {
        n += step;
        if (n >= target) { n = target; clearInterval(t); }
        el.textContent = n;
      }, 25);
      obs.unobserve(el);
    });
  }, { threshold: 0.5 });
  document.querySelectorAll("[data-count]").forEach((el) => obs.observe(el));
})();

/* ---------- Alerts panel ---------- */
const CLASSES = [
  "AnnualCrop", "Forest", "HerbaceousVegetation", "Highway", "Industrial",
  "Pasture", "PermanentCrop", "Residential", "River", "SeaLake",
];

function demoAlerts() {
  const samples = [
    { regiao: "Cerrado — MT", classe: "Pasture", risco: "alto", tipo: "Foco de queimada", conf: 0.93, lat: -13.2, lon: -56.1 },
    { regiao: "Vale do Itajaí — SC", classe: "River", risco: "alto", tipo: "Risco de enchente", conf: 0.89, lat: -27.0, lon: -49.1 },
    { regiao: "Amazônia — PA", classe: "Forest", risco: "baixo", tipo: "Vegetação saudável", conf: 0.97, lat: -3.4, lon: -52.3 },
    { regiao: "Pantanal — MS", classe: "HerbaceousVegetation", risco: "medio", tipo: "Solo seco", conf: 0.81, lat: -18.5, lon: -56.6 },
    { regiao: "Litoral — BA", classe: "SeaLake", risco: "baixo", tipo: "Corpo d'água estável", conf: 0.95, lat: -13.0, lon: -38.5 },
    { regiao: "Grande SP", classe: "Residential", risco: "medio", tipo: "Área urbana monitorada", conf: 0.88, lat: -23.5, lon: -46.6 },
  ];
  return {
    source: "demo",
    generated_at: new Date().toISOString(),
    alerts: samples.map((s, i) => ({
      id: "demo-" + i,
      timestamp: new Date(Date.now() - i * 6e5).toISOString(),
      ...s,
    })),
  };
}

function riskClass(r) {
  return r === "alto" ? "risk-alto" : r === "medio" ? "risk-medio" : "risk-baixo";
}

function render(data) {
  const wrap = document.getElementById("alerts");
  wrap.innerHTML = "";
  data.alerts.forEach((a, i) => {
    const div = document.createElement("div");
    div.className = `alert ${riskClass(a.risco)}`;
    div.style.animationDelay = i * 60 + "ms";
    div.innerHTML = `
      <div class="a-head">
        <span class="a-class">${a.regiao}</span>
        <span class="a-badge">${a.risco}</span>
      </div>
      <div class="a-meta">
        ⚠️ ${a.tipo}<br>
        Cobertura: ${a.classe}<br>
        Lat ${a.lat?.toFixed?.(1) ?? a.lat} · Lon ${a.lon?.toFixed?.(1) ?? a.lon}<br>
        ${new Date(a.timestamp).toLocaleString("pt-BR")}
      </div>
      <div class="a-conf" title="Confiança do modelo"><i style="width:${Math.round((a.conf || 0) * 100)}%"></i></div>
    `;
    wrap.appendChild(div);
  });
  const meta = document.getElementById("panelMeta");
  const when = new Date(data.generated_at || Date.now()).toLocaleTimeString("pt-BR");
  meta.textContent = `${data.alerts.length} alertas · varredura ${when} · fonte: ${data.source}`;
}

function setStatus(state) {
  const pill = document.getElementById("apiStatus");
  pill.className = "status-pill " + (state === "ok" ? "ok" : state === "demo" ? "demo" : "");
  pill.querySelector(".dot");
  pill.innerHTML = `<span class="dot"></span> ${
    state === "ok" ? "API online" : state === "demo" ? "modo demonstração" : "conectando…"
  }`;
}

async function loadAlerts() {
  if (!API_BASE_URL) {
    setStatus("demo");
    render(demoAlerts());
    return;
  }
  try {
    const res = await fetch(`${API_BASE_URL}/alerts`, { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    setStatus("ok");
    render({ source: "api", ...data });
  } catch (err) {
    console.warn("API indisponível, usando demo:", err);
    setStatus("demo");
    render(demoAlerts());
  }
}

document.getElementById("refreshBtn").addEventListener("click", loadAlerts);
loadAlerts();
