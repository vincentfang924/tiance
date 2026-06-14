import gc
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from tiance.api import admin, announcements, market, watchlist
from tiance.clients.tianyan import create_tianyan_client
from tiance.config import default_settings
from tiance.db.migrations import migrate
from tiance.errors import data_response, install_error_handlers
from tiance.scheduler.jobs import register_jobs
from tiance.scheduler.runtime import create_scheduler
from tiance.services.admin import AdminService
from tiance.services.announcement import AnnouncementService
from tiance.services.market import MarketService
from tiance.services.watchlist import WatchlistService


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not getattr(app.state, "testing", False):
        app.state.scheduler = create_scheduler()
        app.state.admin_service.scheduler = app.state.scheduler
        register_jobs(app)
        app.state.scheduler.start()
    try:
        yield
    finally:
        scheduler = getattr(app.state, "scheduler", None)
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)


def create_app(testing: bool = False) -> FastAPI:
    app = FastAPI(title="Tiance", version="0.1.0", lifespan=lifespan)
    settings = default_settings(testing=testing)
    if testing and settings.db_path.exists():
        gc.collect()
        settings.db_path.unlink()
    migrate(settings.db_path)
    app.state.testing = testing
    app.state.scheduler = None
    app.state.settings = settings
    app.state.tianyan_client = create_tianyan_client(settings)
    app.state.watchlist_service = WatchlistService(
        settings.db_path,
        app.state.tianyan_client,
    )
    app.state.market_service = MarketService(app.state.tianyan_client)
    app.state.announcement_service = AnnouncementService(
        settings.db_path,
        app.state.tianyan_client,
    )
    app.state.admin_service = AdminService(settings.db_path, scheduler=None)
    install_error_handlers(app)

    @app.get("/api/health")
    def health():
        return data_response({"status": "ok"})

    app.include_router(watchlist.router)
    app.include_router(market.router)
    app.include_router(admin.router)
    app.include_router(announcements.router)
    app.mount(
        "/",
        StaticFiles(directory=settings.root_dir / "tiance" / "web", html=True),
        name="web",
    )

    return app
