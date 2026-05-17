# gupiaofenxi

本地 A 股短线低吸候选仪表盘。

## 第一版能力

- 从近期强势股池中筛选低吸候选。
- 支持价格区间过滤，默认 3-60 元。
- 输出综合分、明日上涨概率、3 日上涨概率、预期涨幅和标签。
- 输出低吸区间、止损位、目标位和触发条件。
- 顶部展示数据状态，包括最后获取时间、成功/失败状态和缓存提示。
- 默认优先用 AkShare 获取 A 股实时行情，失败时回退到 `data/sample` 样例数据。

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

## 说明

当前版本默认优先使用 AkShare 的东方财富 A 股实时行情接口。如果 AkShare 未安装、网络失败或源站返回异常，页面会回退到 `data/sample` 下的样例行情数据，并在数据状态里显示失败和回退记录。

后续可以继续接入通达信、同花顺、东方财富导出的 CSV，让工具结果和你日常看盘软件的数据保持一致。

概率和预期涨幅是基于规则与历史相似思想的模型估计，不是确定性预测。
