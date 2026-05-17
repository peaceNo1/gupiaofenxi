# gupiaofenxi

本地 A 股短线低吸候选仪表盘。

## 第一版能力

- 从近期强势股池中筛选低吸候选。
- 支持价格区间过滤，默认 3-60 元。
- 输出综合分、明日上涨概率、3 日上涨概率、预期涨幅和标签。
- 输出低吸区间、止损位、目标位和触发条件。
- 顶部展示数据状态，包括最后获取时间、成功/失败状态和缓存提示。
- 点击刷新按钮时从东方财富获取最新 A 股行情，写入本地 CSV 后用于仪表盘。

## 安装

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## 运行测试

```powershell
python -m pytest -v
```

## 启动本地仪表盘

```powershell
python -m uvicorn gupiaofenxi.web.app:app --reload --app-dir src
```

打开：

```text
http://127.0.0.1:8000
```

## 使用导出的行情 CSV

如果你想让仪表盘和通达信、同花顺、东方财富里的价格对齐，可以把导出的行情文件保存为：

```text
data/import/daily_quotes.csv
```

CSV 支持这些常见列名：

- 代码 / 证券代码 / symbol / code
- 名称 / 证券名称 / name
- 最新价 / 现价 / 当前价 / 收盘价 / close
- 今开 / 开盘价 / open
- 最高 / 最高价 / high
- 最低 / 最低价 / low
- 成交量 / volume
- 成交额 / amount
- 涨跌幅 / pct_change
- 行业、概念

只要 `data/import/daily_quotes.csv` 存在，仪表盘会优先使用这个文件；没有导入文件时，会回退到 `data/sample`。

## 说明

当前版本不会在打开页面时自动请求外部行情，避免页面被网络卡住。点击“刷新东方财富数据”按钮后，后端会从东方财富接口获取最新行情并写入 `data/import/daily_quotes.csv`；如果刷新失败，页面会显示错误信息，原有数据不受影响。

后续可以继续接入通达信、同花顺、东方财富导出的 CSV，让工具结果和你日常看盘软件的数据保持一致。

概率和预期涨幅是基于规则与历史相似思想的模型估计，不是确定性预测。
