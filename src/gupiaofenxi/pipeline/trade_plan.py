from gupiaofenxi.domain.models import StockQuote, TradePlan


def build_trade_plan(quote: StockQuote) -> TradePlan:
    buy_low = round(quote.close * 0.97, 2)
    buy_high = round(quote.close * 0.995, 2)
    stop_loss = round(buy_low * 0.96, 2)
    target_price = round(quote.close * 1.06, 2)
    return TradePlan(
        buy_low=buy_low,
        buy_high=buy_high,
        stop_loss=stop_loss,
        target_price=target_price,
        trigger="回踩低吸区间且缩量企稳时观察，放量跌破止损位放弃",
    )
