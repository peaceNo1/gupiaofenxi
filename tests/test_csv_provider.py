from pathlib import Path

from gupiaofenxi.data.csv_provider import CsvDataProvider
from gupiaofenxi.domain.models import DataTaskStatus


def test_csv_provider_loads_exported_chinese_columns(tmp_path: Path):
    csv_path = tmp_path / "daily_quotes.csv"
    csv_path.write_text(
        "代码,名称,最新价,今开,最高,最低,成交量,成交额,涨跌幅,行业,概念\n"
        "000001,平安银行,10.99,11.05,11.14,10.96,974700,107000000,-0.54,银行,权重\n"
        "600000,浦发银行,9.07,9.01,9.10,8.96,1000000,120000000,0.55,银行,权重\n",
        encoding="utf-8-sig",
    )

    quotes, status = CsvDataProvider(csv_path).load_daily_quotes()

    assert len(quotes) == 2
    assert quotes[0].symbol == "000001"
    assert quotes[0].name == "平安银行"
    assert quotes[0].close == 10.99
    assert quotes[0].pct_change == -0.54
    assert status.latest("CSV导入行情").status == DataTaskStatus.SUCCESS


def test_csv_provider_computes_temperature_from_export(tmp_path: Path):
    csv_path = tmp_path / "daily_quotes.csv"
    csv_path.write_text(
        "代码,名称,当前价,成交量,成交额,涨跌幅\n"
        "000001,平安银行,10.99,974700,107000000,-0.54\n"
        "600000,浦发银行,9.07,1000000,120000000,0.55\n",
        encoding="utf-8-sig",
    )

    temperature, status = CsvDataProvider(csv_path).load_market_temperature()

    assert temperature == "震荡"
    assert status.latest("CSV市场温度").success_count == 2
