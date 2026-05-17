from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from gupiaofenxi.config import AppSettings
from gupiaofenxi.domain.models import DashboardReport
from gupiaofenxi.pipeline.report import build_dashboard_report
from gupiaofenxi.storage.json_store import JsonStore


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_SETTINGS = AppSettings()


def create_app(sample_dir: Path | None = None, store_root: Path | None = None) -> FastAPI:
    app = FastAPI(title="A 股短线低吸候选仪表盘")
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=BASE_DIR / "templates")
    sample_data_dir = sample_dir or PROJECT_DIR / "data" / "sample"
    store = JsonStore(store_root or PROJECT_DIR / "data" / "local")

    def generate_report(min_price: float, max_price: float) -> tuple[DashboardReport, AppSettings]:
        settings = AppSettings(min_price=min_price, max_price=max_price)
        manual_exclusions = {
            symbol
            for symbol, override in store.load_manual_overrides().items()
            if override.excluded
        }
        report = build_dashboard_report(
            sample_dir=sample_data_dir,
            settings=settings,
            manual_exclusions=manual_exclusions,
        )
        store.save_report(report)
        return report, settings

    @app.get("/", response_class=HTMLResponse)
    def dashboard(
        request: Request,
        min_price: float = DEFAULT_SETTINGS.min_price,
        max_price: float = DEFAULT_SETTINGS.max_price,
    ):
        report, settings = generate_report(min_price, max_price)
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "report": report,
                "settings": settings,
            },
        )

    @app.get("/api/report")
    def api_report(
        min_price: float = DEFAULT_SETTINGS.min_price,
        max_price: float = DEFAULT_SETTINGS.max_price,
    ):
        report, _ = generate_report(min_price, max_price)
        return report

    return app


app = create_app()
