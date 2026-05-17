# gupiaofenxi

本地 A 股短线低吸候选仪表盘。

## 第一版能力

- 从近期强势股池中筛选低吸候选。
- 支持价格区间过滤，默认 3-60 元。
- 输出综合分、明日上涨概率、3 日上涨概率、预期涨幅和标签。
- 输出低吸区间、止损位、目标位和触发条件。
- 顶部展示数据状态，包括最后获取时间、成功/失败状态和缓存提示。

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

当前版本使用 `data/sample` 下的样例行情数据，先保证评分、筛选、数据状态和页面结构可用。后续再接入 AkShare、Tushare 或 CSV 导入。

概率和预期涨幅是基于规则与历史相似思想的模型估计，不是确定性预测。
