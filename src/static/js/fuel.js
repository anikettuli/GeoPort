// Australian Fuel Mode Controller
let fuelData = null;

async function loadFuelData() {
  const container = document.getElementById("fuelListContainer");
  const regionSelect = document.getElementById("fuelRegionSelect");
  if (!container) return;

  container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 12px 0;">Loading Australian fuel prices...</div>`;

  try {
    const res = await fetch("/api/fuel");
    if (!res.ok) throw new Error("API unreachable");

    fuelData = await res.json();
    if (!fuelData || !fuelData.regions || fuelData.regions.length === 0) {
      container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem;">Fuel prices currently unavailable.</div>`;
      return;
    }

    // Populate regions dropdown
    if (regionSelect && regionSelect.options.length <= 1) {
      regionSelect.innerHTML = "";
      fuelData.regions.forEach((r) => {
        const opt = document.createElement("option");
        opt.value = r.region;
        opt.textContent = r.region;
        regionSelect.appendChild(opt);
      });
    }

    const selectedRegion = regionSelect ? regionSelect.value : "All";
    renderFuelPrices(selectedRegion);
  } catch (err) {
    console.error("Error loading fuel data:", err);
    container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem;">Failed to load fuel price data.</div>`;
  }
}

function renderFuelPrices(regionName) {
  const container = document.getElementById("fuelListContainer");
  if (!container || !fuelData) return;

  const reg = fuelData.regions.find((r) => r.region === regionName) || fuelData.regions[0];
  if (!reg || !reg.prices || reg.prices.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem;">No prices found for ${regionName}.</div>`;
    return;
  }

  container.innerHTML = "";
  reg.prices.forEach((item) => {
    const card = document.createElement("div");
    card.className = "fuel-station-card";
    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: baseline;">
        <span style="font-weight: 700; font-size: 0.9rem;">${escapeHtml(item.type)}</span>
        <span class="fuel-price-badge">${item.price !== null ? item.price + "¢" : "N/A"}</span>
      </div>
      <div style="font-size: 0.78rem; color: var(--text-secondary); margin-top: 4px;">
        ${escapeHtml(item.station || item.suburb || "Station")}, ${escapeHtml(item.state || reg.region)}
      </div>
      <div style="font-size: 0.72rem; color: var(--accent-blue); margin-top: 3px;">
        📍 Click to teleport to this area
      </div>
    `;

    card.addEventListener("click", async () => {
      if (item.latitude && item.longitude) {
        setMarkerLocation(item.latitude, item.longitude, true);
        showToast(`Teleported to ${item.station || item.suburb}`);
      } else {
        // Geocode suburb / state
        const query = `${item.suburb || item.station}, ${item.state || reg.region}, Australia`;
        try {
          const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
          const results = await res.json();
          if (results.length > 0) {
            setMarkerLocation(results[0].latitude, results[0].longitude, true);
            showToast(`Teleported to ${query}`);
          }
        } catch (e) {
          showToast(`Could not locate ${query}`);
        }
      }
    });

    container.appendChild(card);
  });
}

function initFuel() {
  const regionSelect = document.getElementById("fuelRegionSelect");
  const tabFuel = document.querySelector('[data-tab="tabFuel"]');

  if (regionSelect) {
    regionSelect.addEventListener("change", (e) => {
      renderFuelPrices(e.target.value);
    });
  }

  if (tabFuel) {
    tabFuel.addEventListener("click", () => {
      if (!fuelData) loadFuelData();
    });
  }
}
