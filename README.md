# GeoPort 🌍

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**GeoPort** is a modern, privacy-focused iOS location simulation and GPS spoofing platform. Built with **FastAPI**, **WebSockets**, **Leaflet**, and **[`pymobiledevice3`](https://github.com/doronz88/pymobiledevice3)**, it provides developers, QA testers, and security researchers with full control over virtual GPS positioning on iOS 16, 17, and 18 devices.

---

## ✨ Features

- **iOS 16, 17 & 18 Support:** Automatic detection and tunneling via CoreDevice RSD (Remote Service Discovery) over USB and Wi-Fi.
- **Location Search (Worldwide):** Instant address and landmark search powered by OpenStreetMap Nominatim and Photon, plus direct coordinate parsing (`lat, lng`).
- **Modern Open Map Sources:** Seamless switching between CARTO Voyager (Light), CARTO Dark Matter (Dark), OpenStreetMap Standard, OpenTopoMap, and Satellite Imagery.
- **Nudge & Joystick Controls:** Clickable compass controls and keyboard navigation (**WASD / Arrow Keys**) with configurable step distances (5m, 10m, 20m, 50m, 100m, 500m).
- **GPX Route Replay:** Drag & drop GPX tracks with real-time waypoint streaming, speed presets (Walking, Running, Cycling, Driving), and play/pause/stop controls.
- **Fuel Mode (Australia):** Real-time Australian fuel price tracking across states (NSW, VIC, QLD, WA, SA, TAS) with 1-click teleportation to stations.
- **100% Local & Privacy-Preserving:** No secret telemetry or UDID exfiltration. Binds strictly to `127.0.0.1` with native TLS validation.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- **Windows Users:** iTunes or Apple Mobile Device Support installed (provides the usbmuxd service).
- **macOS Users:** Xcode Command Line Tools (`xcode-select --install`).

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/anikettuli/GeoPort.git
   cd GeoPort
   ```

2. **Set up a virtual environment:**
   Using [`uv`](https://github.com/astral-sh/uv) (recommended):
   ```bash
   uv venv --python 3.12 .venv
   .venv\Scripts\activate      # On Windows
   # source .venv/bin/activate  # On macOS/Linux
   uv pip install -r requirements.txt
   ```
   Or using standard `pip`:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run GeoPort:**
   ```bash
   python -m src.main
   ```
   Your default web browser will open automatically to `http://127.0.0.1:54321`.

---

## 🛠️ Command-Line Options

```text
usage: main.py [-h] [--host HOST] [--port PORT] [--no-browser] [--wifihost WIFIHOST] [--udid UDID] [--debug]

GeoPort v5.0.0 - Modern iOS Location Simulator

options:
  -h, --help           Show this help message and exit
  --host HOST          Host interface to bind to (default: 127.0.0.1)
  --port PORT          Port to listen on (default: 54321)
  --no-browser         Skip automatically opening the web browser
  --wifihost WIFIHOST  Specify manual Wi-Fi IP address of the iOS device
  --udid UDID          Target specific device by UDID
  --debug              Enable debug logging
```

---

## 🧪 Testing

Run the test suite with `pytest`:
```bash
pytest
```

---

## 🏛️ Architecture

GeoPort v5.0 replaces legacy monolithic scripts with a clean asynchronous architecture:
- **`src/core/`**: Configuration, data models (`Pydantic`), and system-wide settings.
- **`src/services/`**:
  - `device_service.py`: Usbmux & Bonjour discovery, lockdown clients, and AMFI Developer Mode.
  - `tunnel_service.py`: Supervised CoreDevice TCP/QUIC tunnels for iOS 17+.
  - `simulation_service.py`: Location setting/clearing and async GPX route streaming.
  - `external_api_service.py`: Geocoding, fuel prices, and release notifications.
  - `websocket_manager.py`: Real-time bi-directional events to the web UI.
- **`src/api/`**: Typed REST & WebSocket routes.
- **`src/static/` & `src/templates/`**: Modular, responsive CSS & JavaScript UI (no heavy external bundle requirements, offline-resilient).

---

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.
