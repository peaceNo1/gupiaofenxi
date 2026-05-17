from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from gupiaofenxi.config import AppSettings
from gupiaofenxi.pipeline.report import build_dashboard_report


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = Path(__file__).resolve().parents[3]


def create_app() -> FastAPI:
    app = FastAPI(title="A 股短线低吸候选仪表盘")
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=BASE_DIR / "templates")

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request):
        settings = AppSettings()
        report = build_dashboard_report(
            sample_dir=PROJECT_DIR / "data" / "sample",
            settings=settings,
            manual_exclusions=set(),
        )
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "report": report,
                "settings": settings,
            },
        )

    @app.get("/api/report")
    def api_report():
        return build_dashboard_report(
            sample_dir=PROJECT_DIR / "data" / "sample",
            settings=AppSettings(),
            manual_exclusions=set(),
        )

    return app


app = create_app()
