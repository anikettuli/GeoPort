// Main App Coordinator, WebSocket Manager & UI Lifecycle
let ws = null;

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initMap();
  initSearch();
  initDevices();
  initSimulation();
  initFuel();
  initTabs();
  initPanelCollapse();
  initWebSocket();
  initWirelessModal();
  checkSystemInfo();
});

// Wireless iPhone Control Modal
function initWirelessModal() {
  const modal = document.getElementById("wirelessModal");
  const openBtn = document.getElementById("wirelessModalBtn");
  const closeBtn1 = document.getElementById("closeWirelessModalBtn");
  const closeBtn2 = document.getElementById("closeWirelessModalBtn2");
  const copyBtn = document.getElementById("copyMobileUrlBtn");
  const urlDisplay = document.getElementById("mobileUrlDisplay");
  const qrImg = document.getElementById("qrCodeImg");

  if (!modal || !openBtn) return;

  async function openModal() {
    modal.style.display = "flex";
    try {
      const res = await fetch("/api/system/info");
      const info = await res.json();
      const mobileUrl = info.mobile_url || window.location.href;
      if (urlDisplay) urlDisplay.textContent = mobileUrl;
      if (qrImg) {
        qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(mobileUrl)}`;
        qrImg.style.display = "block";
      }
    } catch (e) {
      if (urlDisplay) urlDisplay.textContent = window.location.href;
    }
  }

  function closeModal() {
    modal.style.display = "none";
  }

  openBtn.addEventListener("click", openModal);
  if (closeBtn1) closeBtn1.addEventListener("click", closeModal);
  if (closeBtn2) closeBtn2.addEventListener("click", closeModal);

  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      const url = urlDisplay ? urlDisplay.textContent.trim() : "";
      if (navigator.clipboard && url) {
        navigator.clipboard.writeText(url).then(() => {
          showToast("Mobile URL copied to clipboard!", "success");
        });
      }
    });
  }
}

// Theme Management
function initTheme() {
  const savedTheme = localStorage.getItem("geoport-theme") || "light";
  setTheme(savedTheme);

  const themeBtn = document.getElementById("themeToggleBtn");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      const nextTheme = current === "dark" ? "light" : "dark";
      setTheme(nextTheme);
    });
  }
}

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("geoport-theme", theme);
  const themeBtn = document.getElementById("themeToggleBtn");
  if (themeBtn) {
    themeBtn.innerHTML = theme === "dark" ? "☀️" : "🌙";
  }
  switchMapTheme(theme);
}

// Side Panel Tabs
function initTabs() {
  const tabs = document.querySelectorAll(".panel-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));

      tab.classList.add("active");
      const targetId = tab.dataset.tab;
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add("active");
    });
  });
}

// Collapsible Panel
function initPanelCollapse() {
  const panel = document.getElementById("controlPanel");
  const toggleBtn = document.getElementById("panelToggleBtn");
  if (!panel || !toggleBtn) return;

  toggleBtn.addEventListener("click", () => {
    panel.classList.toggle("collapsed");
    toggleBtn.innerHTML = panel.classList.contains("collapsed") ? "▶" : "◀";
  });
}

// Real-Time WebSocket
function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  function connect() {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WebSocket connected to GeoPort server");
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleWSEvent(msg.event, msg.data);
      } catch (err) {
        console.error("WS message parse error:", err);
      }
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected. Reconnecting in 3 seconds...");
      setTimeout(connect, 3000);
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      ws.close();
    };
  }

  connect();
}

function handleWSEvent(eventType, data) {
  if (eventType === "location_updated") {
    setMarkerLocation(data.latitude, data.longitude, false, true);
    updateSimulationBanner(true, data.latitude, data.longitude);
  } else if (eventType === "location_cleared") {
    updateSimulationBanner(false);
  } else if (eventType === "gpx_step") {
    setMarkerLocation(data.latitude, data.longitude, false, true);
    const progressEl = document.getElementById("gpxProgressInfo");
    if (progressEl) {
      progressEl.textContent = `Point ${data.index + 1} of ${data.total}`;
    }
  } else if (eventType === "gpx_finished") {
    const playBtn = document.getElementById("btnPlayGPX");
    const pauseBtn = document.getElementById("btnPauseGPX");
    if (playBtn) playBtn.style.display = "inline-flex";
    if (pauseBtn) pauseBtn.style.display = "none";
    showToast("Route playback completed!", "success");
  }
}

// System info check (version notifications, shutdown button)
async function checkSystemInfo() {
  const exitBtn = document.getElementById("exitAppBtn");
  if (exitBtn) {
    exitBtn.addEventListener("click", async () => {
      if (!confirm("Are you sure you want to stop GeoPort?")) return;
      showToast("Shutting down GeoPort server...", "info");
      try {
        await fetch("/api/system/shutdown", { method: "POST" });
        setTimeout(() => {
          document.body.innerHTML = `
            <div style="height: 100vh; display: flex; align-items: center; justify-content: center; flex-direction: column; font-family: sans-serif;">
              <h2>GeoPort has shut down.</h2>
              <p style="color: #64748b; margin-top: 8px;">You can now safely close this browser tab.</p>
            </div>
          `;
        }, 800);
      } catch (e) {
        console.error("Shutdown error:", e);
      }
    });
  }

  try {
    const res = await fetch("/api/system/info");
    if (!res.ok) return;
    const info = await res.json();

    if (info.sudo_message) {
      showToast(info.sudo_message, "error");
    }

    if (info.github_version && info.github_version > info.app_version) {
      showToast(`Update Available: GeoPort v${info.github_version}`, "info");
    }

    if (info.github_broadcast) {
      console.log("Broadcast notice:", info.github_broadcast);
    }
  } catch (err) {
    console.debug("System info check skipped:", err);
  }
}

// Toast notification helper
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = "toast";

  const icon = type === "error" ? "❌" : type === "success" ? "✅" : "ℹ️";
  toast.innerHTML = `<span>${icon}</span><span>${escapeHtml(message)}</span>`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "all 0.25s ease";
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}
