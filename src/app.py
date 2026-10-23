import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.api.routes_devices import router as devices_router
from src.api.routes_fuel import router as fuel_router
from src.api.routes_location import router as location_router
from src.api.routes_search import router as search_router
from src.api.routes_system import router as system_router
from src.api.websocket_endpoint import router as ws_router
from src.core.config import APP_NAME, APP_VERSION, PLATFORM_LABEL, logger
from src.services.tunnel_service import tunnel_service

# Handle PyInstaller frozen executable path resolution
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _meipass = Path(sys._MEIPASS)
    if (_meipass / "src" / "templates").exists():
        BASE_DIR = _meipass / "src"
    elif (_meipass / "templates").exists():
        BASE_DIR = _meipass
    else:
        BASE_DIR = Path(__file__).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {APP_NAME} v{APP_VERSION} on {PLATFORM_LABEL}")
    yield
    logger.info(f"Shutting down {APP_NAME}...")
    await tunnel_service.close_all()


def create_app() -> FastAPI:
    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description="Modern iOS Location Simulation & Testing Platform",
        lifespan=lifespan,
    )

    # Allow local cross-origin if frontend is developed separately
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static assets
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Jinja2 Templates
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    # Include routers
    app.include_router(devices_router)
    app.include_router(location_router)
    app.include_router(search_router)
    app.include_router(fuel_router)
    app.include_router(system_router)
    app.include_router(ws_router)

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "app_name": APP_NAME,
                "app_version": APP_VERSION,
                "platform": PLATFORM_LABEL,
            },
        )

    return app
