import asyncio
import json
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from gupiaofenxi.config import AppSettings
from gupiaofenxi.data.csv_provider import CsvDataProvider
from gupiaofenxi.data.eastmoney_refresh import EastmoneyRefreshError, EastmoneyRefresher
from gupiaofenxi.data.fallback_provider import FallbackDataProvider
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
    enable_background_watch: bool = False,
    watch_interval_seconds: float = 5,
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
            FallbackDataProvider(
                primary=CsvDataProvider(import_csv_path),
                fallback=SampleDataProvider(sample_data_dir),
            )
            if import_csv_path.exists()
            else SampleDataProvider(sample_data_dir)
        )
    )

    def generate_report(min_price: float, max_price: float) -> tuple[DashboardReport, AppSettings]:
        return generate_report_with_filters(min_price, max_price, "", "")

    def generate_report_with_filters(
        min_price: float,
        max_price: float,
        symbol_query: str = "",
        name_query: str = "",
    ) -> tuple[DashboardReport, AppSettings]:
        settings = AppSettings(min_price=min_price, max_price=max_price)
        overrides = store.load_manual_overrides()
        manual_exclusions = {symbol for symbol, override in overrides.items() if override.excluded}
        favorite_symbols = {symbol for symbol, override in overrides.items() if override.focus}
        report = build_dashboard_report(
            sample_dir=sample_data_dir,
            settings=settings,
            manual_exclusions=manual_exclusions,
            favorite_symbols=favorite_symbols,
            symbol_query=symbol_query,
            name_query=name_query,
            provider=provider_factory(),
        )
        store.save_report(report)
        return report, settings

    async def refresh_market_data() -> tuple[str, int]:
        try:
            count = await asyncio.to_thread(refresher.refresh)
            return "success", count
        except EastmoneyRefreshError:
            return "error", 0
        except Exception:
            return "error", 0

    def report_payload(report: DashboardReport) -> dict:
        return report.model_dump(mode="json")

    async def watch_loop() -> None:
        while True:
            await refresh_market_data()
            await asyncio.sleep(watch_interval_seconds)

    @app.on_event("startup")
    async def start_background_watch() -> None:
        if enable_background_watch:
            app.state.watch_task = asyncio.create_task(watch_loop())

    @app.on_event("shutdown")
    async def stop_background_watch() -> None:
        task = getattr(app.state, "watch_task", None)
        if task:
            task.cancel()

    @app.get("/", response_class=HTMLResponse)
    def dashboard(
        request: Request,
        min_price: float = DEFAULT_SETTINGS.min_price,
        max_price: float = DEFAULT_SETTINGS.max_price,
        refresh_status: str | None = None,
        refresh_error: str | None = None,
        symbol_query: str = "",
        name_query: str = "",
    ):
        report, settings = generate_report_with_filters(
            min_price, max_price, symbol_query, name_query
        )
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "report": report,
                "settings": settings,
                "refresh_status": refresh_status,
                "refresh_error": refresh_error,
                "symbol_query": symbol_query,
                "name_query": name_query,
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

    @app.get("/api/watch/report")
    def api_watch_report(
        min_price: float = DEFAULT_SETTINGS.min_price,
        max_price: float = DEFAULT_SETTINGS.max_price,
        symbol_query: str = "",
        name_query: str = "",
    ):
        report, _ = generate_report_with_filters(min_price, max_price, symbol_query, name_query)
        return report

    @app.post("/api/watch/refresh")
    async def api_watch_refresh(
        min_price: float = DEFAULT_SETTINGS.min_price,
        max_price: float = DEFAULT_SETTINGS.max_price,
        symbol_query: str = "",
        name_query: str = "",
    ):
        status, count = await refresh_market_data()
        report, _ = generate_report_with_filters(min_price, max_price, symbol_query, name_query)
        return JSONResponse(
            {
                "status": status,
                "refreshed_count": count,
                "report": report_payload(report),
            }
        )

    @app.get("/api/watch/events")
    async def api_watch_events(
        request: Request,
        min_price: float = DEFAULT_SETTINGS.min_price,
        max_price: float = DEFAULT_SETTINGS.max_price,
        symbol_query: str = "",
        name_query: str = "",
    ):
        async def events():
            while not await request.is_disconnected():
                report, _ = generate_report_with_filters(
                    min_price, max_price, symbol_query, name_query
                )
                payload = json.dumps(report_payload(report), ensure_ascii=False)
                yield f"event: report\ndata: {payload}\n\n"
                await asyncio.sleep(3)

        return StreamingResponse(events(), media_type="text/event-stream")

    @app.post("/api/favorites/{symbol}")
    def add_favorite(symbol: str):
        store.set_focus(symbol, True)
        return {"favorites": sorted(store.focused_symbols())}

    @app.delete("/api/favorites/{symbol}")
    def remove_favorite(symbol: str):
        store.set_focus(symbol, False)
        return {"favorites": sorted(store.focused_symbols())}

    return app


app = create_app(enable_background_watch=True)
