import logging
import time
from .models import *
from typing import *
import pandas as pd
from threading import Timer

if TYPE_CHECKING:
    from apis.binance_futures import BinanceFuturesClient

logger = logging.getLogger()

TF = {"1m": 60, "5m": 300, "15m": 1800, "1h": 3600, "4h": 14400}


class Strategy:
    def __init__(
        self,
        client: "BinanceFuturesClient",
        contract: Contract,
        exchange: str,
        timeframe: str,
        balance_pct: float,
        take_profit: float,
        stop_loss: float,
        strategy_name: str,
    ):
        self.client = client

        self.contract = contract
        self.exchange = exchange
        self.tf = timeframe
        self.tf_equiv = TF[timeframe] * 1000
        self.balance_pct = balance_pct
        self.take_profit = take_profit
        self.stop_loss = stop_loss

        self.strategy_name = strategy_name

        self.in_position = False

        self.candles: List[Candle] = []
        self.trades: List[Trade] = []

        self.logs = []

    def _add_log(self, msg: str):
        logger.info(f"{msg}")
        self.logs.append({"log": msg, "displayed": False})

    def parse_trades(self, price: float, size: float, timestamp: int) -> str:
        timestamp_diff = int(time.time() * 1000) - timestamp
        if timestamp_diff >= 2000:
            logger.warning(
                f"{self.exchange} {self.contract.symbol}: {timestamp_diff} ms of difference between the current time and the trade time"
            )

        last_candle = self.candles[-1]

        # same candle
        if timestamp < last_candle.timestamp + self.tf_equiv:
            last_candle.close = price
            last_candle.volume += size

            if price > last_candle.high:
                last_candle.high = price
            elif price < last_candle.low:
                last_candle.low = price

            return "same_candle"

        # missing candle(s)
        elif timestamp >= last_candle.timestamp + self.tf_equiv:
            missing_candles = (
                int((timestamp - last_candle.timestamp) / self.tf_equiv) - 1
            )

            logger.info(
                f"{self.exchange} missing {missing_candles} candles for {self.contract.symbol} {self.tf} ({timestamp} {last_candle.timestamp})"
            )

            for missing in range(missing_candles):
                new_ts = last_candle.timestamp + self.tf_equiv
                candle_info = {
                    "ts": new_ts,
                    "open": last_candle.close,
                    "high": last_candle.close,
                    "low": last_candle.close,
                    "close": last_candle.close,
                    "volume": 0,
                }
                new_candle = Candle(candle_info, self.tf, "parse_trade")
                self.candles.append(new_candle)

                last_candle = new_candle

            new_ts = last_candle.timestamp + self.tf_equiv
            candle_info = {
                "ts": new_ts,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": size,
            }
            new_candle = Candle(candle_info, self.tf, "parse_trade")

            self.candles.append(new_candle)

            return "new_candle"

        # new candle
        elif timestamp > last_candle.timestamp + self.tf_equiv:
            new_ts = last_candle.timestamp + self.tf_equiv
            candle_info = {
                "ts": new_ts,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": size,
            }
            new_candle = Candle(candle_info, self.tf, "parse_trade")

            self.candles.append(new_candle)

            logger.info(
                f"{self.exchange}: New candle for {self.contract.symbol} {self.tf}"
            )
            return "new_candle"

    def _rsi(self, rsi_length):
        close_prices = []

        for candle in self.candles:
            close_prices.append(candle.close)

        closes = pd.Series(close_prices)

        delta = closes.diff().dropna()

        up, down = delta.copy(), delta.copy()

        up[up < 0] = 0
        down[down > 0] = 0

        avg_gain = up.abs().ewm(com=(rsi_length - 1), min_periods=rsi_length).mean()
        avg_loss = down.abs().ewm(com=(rsi_length - 1), min_periods=rsi_length).mean()

        rs = avg_gain / avg_loss

        rsi = 100 - 100 / (1 + rs)
        rsi = rsi.round(2)

        return rsi.iloc[-2]

    def _macd(self, ema_fast, ema_slow, ema_signal) -> Tuple[float, float]:
        close_prices = []

        for candle in self.candles:
            close_prices.append(candle.close)

        closes = pd.Series(close_prices)

        ema_fast = closes.ewm(span=ema_fast).mean()
        ema_slow = closes.ewm(span=ema_slow).mean()

        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=ema_signal).mean()

        return macd_line.iloc[-2], macd_signal.iloc[-2]

    def _check_order_status(self, order_id):
        order_status = self.client.get_order_status(self.contract, order_id)
        if order_status is not None:
            logger.info(f"{self.exchange} order status: {order_status.status}")
            if order_status.status == "filled":
                for trade in self.trades:
                    if trade.entry_id == order_id:
                        trade.entry_price = order_status.avg_price
                        break

                return

        t = Timer(2.0, lambda: self._check_order_status(order_id))
        t.start()

    def _open_position(self, signal_result: int):
        trade_size = self.client.get_trade_size(
            self.contract, self.candles[-1].close, self.balance_pct
        )

        if trade_size is None:
            return

        order_side = "buy" if signal_result == 1 else "sell"
        position_side = "long" if signal_result == 1 else "short"

        self._add_log(
            f"{position_side.capitalize()} signal on {self.contract.symbol} {self.tf}"
        )

        order_status = self.client.place_order(
            self.contract, "MARKET", trade_size, order_side
        )

        if order_status is not None:
            self._add_log(
                f"{order_status.capitalize()} order placed on {self.exchange}\n\
                \t\tStatus: {order_status.status}"
            )

            self.in_position = True

            avg_fill_price = None
            if order_status.status in ["filled", "executed"]:
                avg_fill_price = order_status.avg_price
            else:
                t = Timer(2.0, lambda: self._check_order_status(order_status.order_id))
                t.start()

            new_trade = Trade(
                {
                    "time": int(time.time() * 1000),
                    "entry_price": avg_fill_price,
                    "contract": self.contract,
                    "strategy": self.strategy_name,
                    "side": position_side,
                    "status": "open",
                    "pnl": 0,
                    "quantity": trade_size,
                    "entry_id": order_status.order_id,
                }
            )
            self.trades.append(new_trade)


class TechnicalStrategy(Strategy):
    def __init__(
        self,
        client,
        contract: Contract,
        exchange: str,
        timeframe: str,
        balance_pct: float,
        take_profit: float,
        stop_loss: float,
        other_params: Dict,
    ):
        super().__init__(
            client,
            contract,
            exchange,
            timeframe,
            balance_pct,
            take_profit,
            stop_loss,
            "Technical",
        )

        self._ema_fast = other_params["ema_fast"]
        self._ema_slow = other_params["ema_slow"]
        self._ema_signal = other_params["ema_signal"]

        self._rsi_length = other_params["rsi_length"]

        print(f"Activated Technical Strategy for {contract.symbol}")

    def _check_signal(self) -> int:
        macd_line, macd_signal = self._macd(
            self._ema_fast, self._ema_slow, self._ema_signal
        )
        rsi = self._rsi(self._rsi_length)

        if rsi < 30 and macd_line > macd_signal:
            return 1
        elif rsi > 70 and macd_line < macd_signal:
            return -1
        else:
            return 0

    def check_trade(self, tick_type: str):
        if tick_type == "new candle" and not self.in_position:
            signal_res = self._check_signal()

            if signal_res in [-1, 1]:
                self._open_position(signal_res)


class BreakoutStrategy(Strategy):
    def __init__(
        self,
        client,
        contract: Contract,
        exchange: str,
        timeframe: str,
        balance_pct: float,
        take_profit: float,
        stop_loss: float,
        other_params: Dict,
    ):
        super().__init__(
            client,
            contract,
            exchange,
            timeframe,
            balance_pct,
            take_profit,
            stop_loss,
            "Breakout",
        )

        self._min_volume = other_params["min_volume"]
        print(f"Activated Breakout Strategy for {contract.symbol}")

    def _check_signal(self) -> int:
        if (
            self.candles[-1].close > self.candles[-2].high
            and self.candles[-1].volume > self._min_volume
        ):
            return 1
        elif (
            self.candles[-1].close < self.candles[-2].low
            and self.candles[-1].volume > self._min_volume
        ):
            return -1
        else:
            return 0

    def check_trade(self, tick_type: str):
        if not self.in_position:
            signal_res = self._check_signal()

            if signal_res in [-1, 1]:
                self._open_position(signal_res)


class VWAPStrategy(Strategy):
    def __init__(
        self,
        client,
        contract: Contract,
        exchange: str,
        timeframe: str,
        balance_pct: float,
        take_profit: float,
        stop_loss: float,
        other_params: Dict,
    ):
        super().__init__(
            client,
            contract,
            exchange,
            timeframe,
            balance_pct,
            take_profit,
            stop_loss,
            "VWAP",
        )
        self._days_before_vwap = other_params["days_before_vwap"]
        self._days_before_ema = other_params["days_before_ema"]
        print(f"Activated VWAP Strategy for {contract.symbol}")

    def _check_signal(self) -> int:
        pass

    def check_trade(self, tick_type: str):
        pass
