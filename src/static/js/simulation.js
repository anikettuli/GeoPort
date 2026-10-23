// Simulation Controller: Single-point spoofing, Nudging, Keyboard Joystick, & GPX routes
let currentStepMeters = 20.0;
let loadedGPXWaypoints = [];
let isSimulatingActive = false;

function initSimulation() {
  const btnSimulate = document.getElementById("btnSimulateLocation");
  const btnStop = document.getElementById("btnStopLocation");
  const gpxFileInput = document.getElementById("gpxFileInput");
  const btnPlayGPX = document.getElementById("btnPlayGPX");
  const btnPauseGPX = document.getElementById("btnPauseGPX");
  const btnStopGPX = document.getElementById("btnStopGPX");

  // Step size selection
  document.querySelectorAll(".step-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      document.querySelectorAll(".step-pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      currentStepMeters = parseFloat(pill.dataset.step) || 20.0;
      showToast(`Step distance: ${currentStepMeters}m`);
    });
  });

  // Joystick buttons
  document.querySelectorAll(".joystick-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const dir = btn.dataset.direction;
      if (dir) nudgeLocation(dir);
    });
  });

  // Keyboard Joystick (WASD & Arrows)
  window.addEventListener("keydown", (e) => {
    // Ignore keystrokes when focused inside input fields or textareas
    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
      return;
    }

    if (e.key === "ArrowUp" || e.key.toLowerCase() === "w") {
      e.preventDefault();
      nudgeLocation("north");
    } else if (e.key === "ArrowDown" || e.key.toLowerCase() === "s") {
      e.preventDefault();
      nudgeLocation("south");
    } else if (e.key === "ArrowLeft" || e.key.toLowerCase() === "a") {
      e.preventDefault();
      nudgeLocation("west");
    } else if (e.key === "ArrowRight" || e.key.toLowerCase() === "d") {
      e.preventDefault();
      nudgeLocation("east");
    }
  });

  // Simulate button
  if (btnSimulate) {
    btnSimulate.addEventListener("click", async () => {
      if (!selectedDeviceUDID) {
        showToast("Please select a connected device", "error");
        return;
      }
      const lat = parseFloat(document.getElementById("inputLat").value);
      const lng = parseFloat(document.getElementById("inputLng").value);
      if (isNaN(lat) || isNaN(lng)) {
        showToast("Invalid latitude or longitude", "error");
        return;
      }

      btnSimulate.disabled = true;
      try {
        const res = await fetch(`/api/devices/${selectedDeviceUDID}/location`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ latitude: lat, longitude: lng }),
        });
        const data = await res.json();
        if (res.ok) {
          isSimulatingActive = true;
          setMarkerLocation(lat, lng, false, true);
          updateSimulationBanner(true, lat, lng);
          showToast(`Location set: ${lat.toFixed(5)}, ${lng.toFixed(5)}`, "success");
        } else {
          showToast(data.detail || "Failed to set location", "error");
        }
      } catch (err) {
        showToast("Network error setting location", "error");
      } finally {
        btnSimulate.disabled = false;
      }
    });
  }

  // Stop button
  if (btnStop) {
    btnStop.addEventListener("click", async () => {
      if (!selectedDeviceUDID) return;
      try {
        const res = await fetch(`/api/devices/${selectedDeviceUDID}/location`, {
          method: "DELETE",
        });
        if (res.ok) {
          isSimulatingActive = false;
          const pos = currentMarker.getLatLng();
          setMarkerLocation(pos.lat, pos.lng, false, false);
          updateSimulationBanner(false);
          clearGPXRoute();
          showToast("Simulation stopped. Real GPS restored.", "info");
        }
      } catch (err) {
        showToast("Error stopping simulation", "error");
      }
    });
  }

  // GPX File Input
  if (gpxFileInput) {
    gpxFileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        parseGPXText(event.target.result);
      };
      reader.readAsText(file);
    });
  }

  // GPX Play controls
  if (btnPlayGPX) {
    btnPlayGPX.addEventListener("click", async () => {
      if (!selectedDeviceUDID) {
        showToast("Select a device first", "error");
        return;
      }
      if (loadedGPXWaypoints.length === 0) {
        showToast("Please load a GPX file first", "error");
        return;
      }

      const speedVal = parseFloat(document.getElementById("gpxSpeedSelect").value) || 1.4;
      const waypoints = loadedGPXWaypoints.map((wp) => ({
        latitude: wp.latitude,
        longitude: wp.longitude,
        speed_mps: speedVal,
      }));

      try {
        const res = await fetch(`/api/devices/${selectedDeviceUDID}/route/play`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ waypoints, loop: false, speed_multiplier: 1.0 }),
        });
        if (res.ok) {
          btnPlayGPX.style.display = "none";
          if (btnPauseGPX) btnPauseGPX.style.display = "inline-flex";
          showToast("GPX playback started", "success");
        }
      } catch (err) {
        showToast("Failed to start GPX playback", "error");
      }
    });
  }

  if (btnPauseGPX) {
    btnPauseGPX.addEventListener("click", async () => {
      if (!selectedDeviceUDID) return;
      const isPaused = btnPauseGPX.dataset.paused === "true";
      const endpoint = isPaused ? "resume" : "pause";
      try {
        const res = await fetch(`/api/devices/${selectedDeviceUDID}/route/${endpoint}`, {
          method: "POST",
        });
        if (res.ok) {
          btnPauseGPX.dataset.paused = isPaused ? "false" : "true";
          btnPauseGPX.textContent = isPaused ? "⏸ Pause" : "▶ Resume";
        }
      } catch (err) {
        showToast("Error pausing route", "error");
      }
    });
  }

  if (btnStopGPX) {
    btnStopGPX.addEventListener("click", async () => {
      if (!selectedDeviceUDID) return;
      try {
        await fetch(`/api/devices/${selectedDeviceUDID}/route/stop`, { method: "POST" });
        if (btnPlayGPX) btnPlayGPX.style.display = "inline-flex";
        if (btnPauseGPX) {
          btnPauseGPX.style.display = "none";
          btnPauseGPX.dataset.paused = "false";
          btnPauseGPX.textContent = "⏸ Pause";
        }
        showToast("GPX playback stopped", "info");
      } catch (err) {
        showToast("Error stopping route", "error");
      }
    });
  }
}

async function nudgeLocation(direction) {
  if (!selectedDeviceUDID) {
    showToast("Please select a device to move location", "error");
    return;
  }

  try {
    const res = await fetch(`/api/devices/${selectedDeviceUDID}/nudge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction, distance_meters: currentStepMeters }),
    });
    const data = await res.json();
    if (res.ok) {
      setMarkerLocation(data.latitude, data.longitude, false, true);
      updateSimulationBanner(true, data.latitude, data.longitude);
    }
  } catch (err) {
    console.error("Nudge error:", err);
  }
}

function parseGPXText(gpxString) {
  try {
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(gpxString, "text/xml");
    const points = [];

    // Check trackpoints <trkpt>
    let ptNodes = xmlDoc.querySelectorAll("trkpt");
    if (ptNodes.length === 0) {
      // Fallback to routepoints <rtept> or waypoints <wpt>
      ptNodes = xmlDoc.querySelectorAll("rtept, wpt");
    }

    ptNodes.forEach((node) => {
      const lat = parseFloat(node.getAttribute("lat"));
      const lon = parseFloat(node.getAttribute("lon"));
      if (!isNaN(lat) && !isNaN(lon)) {
        points.push({ latitude: lat, longitude: lon, speed_mps: 1.4 });
      }
    });

    if (points.length === 0) {
      showToast("No valid coordinates found in GPX file", "error");
      return;
    }

    loadedGPXWaypoints = points;
    renderGPXRoute(points);
    setMarkerLocation(points[0].latitude, points[0].longitude, true);

    const infoEl = document.getElementById("gpxFileInfo");
    if (infoEl) {
      infoEl.textContent = `Loaded route: ${points.length} waypoints`;
    }
    showToast(`Loaded ${points.length} waypoints from GPX!`, "success");
  } catch (err) {
    showToast("Failed to parse GPX XML", "error");
  }
}

function updateSimulationBanner(isActive, lat = null, lng = null) {
  const banner = document.getElementById("simulationBanner");
  if (!banner) return;

  if (isActive) {
    banner.className = "status-banner status-active";
    banner.innerHTML = `🟢 Spoofing active: <b>${lat ? lat.toFixed(5) : ""}, ${lng ? lng.toFixed(5) : ""}</b>`;
  } else {
    banner.className = "status-banner status-idle";
    banner.innerHTML = `⚪ Location simulation is currently inactive.`;
  }
}
