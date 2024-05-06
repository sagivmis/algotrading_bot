class Balance:
    def __init__(self, info):
        self.initial_margin = float(info["initialMargin"])
        self.maintenance_margin = float(info["maintMargin"])
        self.margin_balance = float(info["maginBalance"])
        self.wallet.balance = float(info["walletBalance"])
        self.unrealized_pnl = float(info["unrealizedProfit"])


class Candle:
    def __init__(self, info, exchange="Binance"):
        if exchange == "Binance":
            self.timestamp = info[0]
            self.open = float(info[1])
            self.high = float(info[2])
            self.low = float(info[3])
            self.close = float(info[4])
            self.volume = float(info[5])

        elif exchange == "parse_trade":
            self.timestamp = info["ts"]
            self.open = float(info["open"])
            self.high = float(info["high"])
            self.low = float(info["low"])
            self.close = float(info["close"])
            self.volume = float(info["volume"])


class Contract:
    def __init__(self, info, exchange: str) -> None:
        self.symbol = info["symbol"]
        self.base_asset = info["baseAsset"]
        self.quote_asset = info["quoteAsset"]
        self.price_decimals = info["pricePrecision"]
        self.quantity_decimals = info["quantityPrecision"]
        self.tick_size = 1 / pow(10, info["pricePrecision"])
        self.lot_size = 1 / pow(10, info["quantityPrecision"])

        self.exchange = exchange


class OrderStatus:
    def __init__(self, info) -> None:
        self.order_id: str = info["orderId"]
        self.status: str = info["status"].lower()
        self.avg_price: float = info["avgPrice"]


class Trade:
    def __init__(self, info) -> None:
        self.time: int = info["time"]
        self.contract: Contract = info["contract"]
        self.strategy: str = info["strategy"]
        self.side: str = info["side"]
        self.entry_price: float = info["entry_price"]
        self.status: str = info["status"]
        self.pnl: float = info["pnl"]
        self.quantity = info["quantity"]
        self.entry_id = info["entry_id"]
