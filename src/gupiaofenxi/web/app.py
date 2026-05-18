from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from gupiaofenxi.config import AppSettings
from gupiaofenxi.data.csv_provider import CsvDataProvider
from gupiaofenxi.data.eastmoney_refresh import EastmoneyRefreshError, EastmoneyRefresher
from gupiaofenxi.data.sample_provider import SampleDataProvider
from gupiaofenxi.domain.models import DashboardReport
from gupiaofenxi.pipeline.report import build_dashboard_report
from gupiaofenxi.storage.json_store import JsonStore


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_SETTINGS = AppSettings()


def create_app(
    sample_dir: Path | None = None,
    store_root: Path | None = None,
    provider_factory=None,
    refresher=None,
) -> FastAPI:
    app = FastAPI(title="A 股短线低吸候选仪表盘")
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=BASE_DIR / "templates")
    sample_data_dir = sample_dir or PROJECT_DIR / "data" / "sample"
    import_csv_path = PROJECT_DIR / "data" / "import" / "daily_quotes.csv"
    store = JsonStore(store_root or PROJECT_DIR / "data" / "local")
    refresher = refresher or EastmoneyRefresher(
        import_csv_path, symbols_csv_path=sample_data_dir / "daily_quotes.csv"
    )
    provider_factory = provider_factory or (
        lambda: (
            CsvDataProvider(import_csv_path)
            if import_csv_path.exists()
            else SampleDataProvider(sample_data_dir)
        )
    )

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
            provider=provider_factory(),
        )
        store.save_report(report)
        return report, settings

    @app.get("/", response_class=HTMLResponse)
    def dashboard(
        request: Request,
        min_price: float = DEFAULT_SETTINGS.min_price,
        max_price: float = DEFAULT_SETTINGS.max_price,
        refresh_status: str | None = None,
        refresh_error: str | None = None,
    ):
        report, settings = generate_report(min_price, max_price)
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "report": report,
                "settings": settings,
                "refresh_status": refresh_status,
                "refresh_error": refresh_error,
            },
        )

    def refresh_response(min_price: float, max_price: float) -> RedirectResponse:
        params = {"min_price": min_price, "max_price": max_price}
        try:
            count = refresher.refresh()
            params["refresh_status"] = f"已从东方财富刷新 {count} 条行情"
        except EastmoneyRefreshError as exc:
            params["refresh_error"] = str(exc)
        except Exception:
            params["refresh_error"] = "东方财富刷新失败：网络连接异常，请稍后重试；当前继续使用已有数据"
        return RedirectResponse(url="/?" + urlencode(params), status_code=303)

    @app.get("/refresh")
    def refresh_data_get(
        min_price: float = DEFAULT_SETTINGS.min_price,
        max_price: float = DEFAULT_SETTINGS.max_price,
    ):
        return refresh_response(min_price, max_price)

    @app.post("/refresh")
    def refresh_data_post(
        min_price: float = DEFAULT_SETTINGS.min_price,
        max_price: float = DEFAULT_SETTINGS.max_price,
    ):
        return refresh_response(min_price, max_price)

    @app.get("/api/report")
    def api_report(
        min_price: float = DEFAULT_SETTINGS.min_price,
        max_price: float = DEFAULT_SETTINGS.max_price,
    ):
        report, _ = generate_report(min_price, max_price)
        return report

    return app


app = create_app()
