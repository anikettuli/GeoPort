// Device Management & Lockdown Controller
let connectedDevices = [];
let selectedDeviceUDID = null;

async function loadDevices() {
  const deviceSelect = document.getElementById("deviceSelect");
  const refreshBtn = document.getElementById("refreshDevicesBtn");
  if (!deviceSelect) return;

  if (refreshBtn) refreshBtn.classList.add("spinning");

  try {
    const res = await fetch("/api/devices");
    if (!res.ok) throw new Error("Failed to load devices");

    connectedDevices = await res.json();
    deviceSelect.innerHTML = "";

    if (connectedDevices.length === 0) {
      deviceSelect.innerHTML = `<option value="">No iOS Devices Found (Connect via USB)</option>`;
      selectedDeviceUDID = null;
      updateDeviceUI(null);
      return;
    }

    connectedDevices.forEach((dev) => {
      const opt = document.createElement("option");
      opt.value = dev.udid;
      const connIcon = dev.connection_type === "WiFi" ? "📶 Wi-Fi" : "🔌 USB";
      opt.textContent = `${dev.name} (iOS ${dev.product_version}) - ${connIcon}`;
      deviceSelect.appendChild(opt);
    });

    // Select first or keep existing
    if (!selectedDeviceUDID || !connectedDevices.some((d) => d.udid === selectedDeviceUDID)) {
      selectedDeviceUDID = connectedDevices[0].udid;
    }
    deviceSelect.value = selectedDeviceUDID;
    updateDeviceUI(getCurrentDevice());
  } catch (err) {
    console.error("Device discovery error:", err);
    deviceSelect.innerHTML = `<option value="">Error discovering devices</option>`;
  } finally {
    if (refreshBtn) refreshBtn.classList.remove("spinning");
  }
}

function getCurrentDevice() {
  return connectedDevices.find((d) => d.udid === selectedDeviceUDID) || null;
}

function initDevices() {
  const deviceSelect = document.getElementById("deviceSelect");
  const refreshBtn = document.getElementById("refreshDevicesBtn");
  const enableDevModeBtn = document.getElementById("enableDevModeBtn");
  const mountDiskBtn = document.getElementById("mountDiskBtn");

  if (deviceSelect) {
    deviceSelect.addEventListener("change", (e) => {
      selectedDeviceUDID = e.target.value;
      updateDeviceUI(getCurrentDevice());
    });
  }

  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      loadDevices();
      showToast("Scanning for devices...");
    });
  }

  if (enableDevModeBtn) {
    enableDevModeBtn.addEventListener("click", async () => {
      if (!selectedDeviceUDID) {
        showToast("Please select an iOS device first", "error");
        return;
      }
      showToast("Enabling Developer Mode on device...", "info");
      try {
        const res = await fetch(`/api/devices/${selectedDeviceUDID}/developer-mode`, {
          method: "POST",
        });
        const data = await res.json();
        if (res.ok) {
          showToast("Developer Mode enabled! Please follow any on-screen prompts.", "success");
          loadDevices();
        } else {
          showToast(data.detail || "Failed to enable Developer Mode", "error");
        }
      } catch (err) {
        showToast("Network error enabling Developer Mode", "error");
      }
    });
  }

  if (mountDiskBtn) {
    mountDiskBtn.addEventListener("click", async () => {
      if (!selectedDeviceUDID) {
        showToast("Please select an iOS device first", "error");
        return;
      }
      showToast("Mounting Developer Disk Image...", "info");
      try {
        const res = await fetch(`/api/devices/${selectedDeviceUDID}/mount`, {
          method: "POST",
        });
        const data = await res.json();
        if (res.ok) {
          showToast("Developer Disk Image mounted successfully!", "success");
        } else {
          showToast(data.detail || "Failed to mount disk image", "error");
        }
      } catch (err) {
        showToast("Network error mounting disk image", "error");
      }
    });
  }

  loadDevices();
}

function updateDeviceUI(device) {
  const devBanner = document.getElementById("devModeWarningBanner");
  const simulateBtn = document.getElementById("btnSimulateLocation");

  if (!device) {
    if (devBanner) devBanner.style.display = "none";
    if (simulateBtn) simulateBtn.disabled = true;
    return;
  }

  if (simulateBtn) simulateBtn.disabled = false;

  // Check if developer mode is false and version >= 16
  const majorVersion = parseInt(device.product_version.split(".")[0], 10) || 16;
  if (majorVersion >= 16 && !device.developer_mode) {
    if (devBanner) devBanner.style.display = "flex";
  } else {
    if (devBanner) devBanner.style.display = "none";
  }
}
