from binance.client import Client
from binance import ThreadedWebsocketManager
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

api_key = "HBGr41CUustXVNMeTtF89oiQCB27MhyrZX8nmjwilRwex4wCjUQzpOZ0XCdSvnQH"
secret_key = "qWo11IuaHwBxvL9YaPMeWrA1l5JujEswbJcWjrAo7m9Wwz0acwbmnPmFeu55TPq3"
client = Client(api_key=api_key, api_secret=secret_key, tld="com", testnet=True)


class Trader:
    def __init__(
        self, symbol, bar_length, sma_s, sma_m, sma_l, units, position=0, leverage=5
    ):
        self.symbol = symbol
        self.bar_length = bar_length
        self.available_intervals = [
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "6h",
            "8h",
            "12h",
            "1d",
            "3d",
            "1w",
            "1M",
        ]
        self.units = units
        self.position = position
        self.leverage = leverage
        self.cum_profits = 0

        # *****************add strategy-specific attributes here******************
        self.SMA_S = sma_s
        self.SMA_M = sma_m
        self.SMA_L = sma_l
        # ************************************************************************

    def start_trading(self, historical_days):
        client.futures_change_leverage(symbol=self.symbol, leverage=self.leverage)

        self.twm = ThreadedWebsocketManager()
        self.twm.start()

        if self.bar_length in self.available_intervals:
            self.get_most_recent(
                symbol=self.symbol, interval=self.bar_length, days=historical_days
            )
            self.twm.start_kline_futures_socket(
                callback=self.stream_candles,
                symbol=self.symbol,
                interval=self.bar_length,
            )  # Adj: start_kline_futures_socket
            self.twm.join()

        # "else" to be added later in the course

    def get_most_recent(self, symbol, interval, days):
        now = datetime.utcnow()
        past = str(now - timedelta(days=days))

        bars = client.futures_historical_klines(
            symbol=symbol, interval=interval, start_str=past, end_str=None, limit=1000
        )  # Adj: futures_historical_klines
        df = pd.DataFrame(bars)
        df["Date"] = pd.to_datetime(df.iloc[:, 0], unit="ms")
        df.columns = [
            "Open Time",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "Clos Time",
            "Quote Asset Volume",
            "Number of Trades",
            "Taker Buy Base Asset Volume",
            "Taker Buy Quote Asset Volume",
            "Ignore",
            "Date",
        ]
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
        df.set_index("Date", inplace=True)
        for column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        df["Complete"] = [True for row in range(len(df) - 1)] + [False]

        self.data = df

    def stream_candles(self, msg):
        # extract the required items from msg
        event_time = pd.to_datetime(msg["E"], unit="ms")
        start_time = pd.to_datetime(msg["k"]["t"], unit="ms")
        first = float(msg["k"]["o"])
        high = float(msg["k"]["h"])
        low = float(msg["k"]["l"])
        close = float(msg["k"]["c"])
        volume = float(msg["k"]["v"])
        complete = msg["k"]["x"]

        # stop trading session
        if event_time >= datetime(2023, 8, 22, 12, 26):
            self.twm.stop()
            if self.position == 1:
                order = client.futures_create_order(
                    symbol=self.symbol, side="SELL", type="MARKET", quantity=self.units
                )
                self.report_trade(order, "GOING NEUTRAL AND STOP")
                self.position = 0
            elif self.position == -1:
                order = client.futures_create_order(
                    symbol=self.symbol, side="BUY", type="MARKET", quantity=self.units
                )
                self.report_trade(order, "GOING NEUTRAL AND STOP")
                self.position = 0
            else:
                print("STOP")

        else:
            # print out
            print(
                ".", end="", flush=True
            )  # just print something to get a feedback (everything OK)

            # feed df (add new bar / update latest bar)
            self.data.loc[start_time] = [first, high, low, close, volume, complete]

            # prepare features and define strategy/trading positions whenever the latest bar is complete
            if complete == True:
                self.define_strategy()
                self.execute_trades()

    def define_strategy(self):
        data = self.data.copy()

        # ******************** define your strategy here ************************
        data = data[["Close"]].copy()

        data["SMA_S"] = data.Close.rolling(window=self.SMA_S).mean()
        data["SMA_M"] = data.Close.rolling(window=self.SMA_M).mean()
        data["SMA_L"] = data.Close.rolling(window=self.SMA_L).mean()

        data.dropna(inplace=True)

        cond1 = (data.SMA_S > data.SMA_M) & (data.SMA_M > data.SMA_L)
        cond2 = (data.SMA_S < data.SMA_M) & (data.SMA_M < data.SMA_L)

        data["position"] = 0
        data.loc[cond1, "position"] = 1
        data.loc[cond2, "position"] = -1
        # ***********************************************************************

        self.prepared_data = data.copy()

    def execute_trades(self):
        if (
            self.prepared_data["position"].iloc[-1] == 1
        ):  # if position is long -> go/stay long
            if self.position == 0:
                order = client.futures_create_order(
                    symbol=self.symbol, side="BUY", type="MARKET", quantity=self.units
                )
                self.report_trade(order, "GOING LONG")
            elif self.position == -1:
                order = client.futures_create_order(
                    symbol=self.symbol,
                    side="BUY",
                    type="MARKET",
                    quantity=2 * self.units,
                )
                self.report_trade(order, "GOING LONG")
            self.position = 1
        elif (
            self.prepared_data["position"].iloc[-1] == 0
        ):  # if position is neutral -> go/stay neutral
            if self.position == 1:
                order = client.futures_create_order(
                    symbol=self.symbol, side="SELL", type="MARKET", quantity=self.units
                )
                self.report_trade(order, "GOING NEUTRAL")
            elif self.position == -1:
                order = client.futures_create_order(
                    symbol=self.symbol, side="BUY", type="MARKET", quantity=self.units
                )
                self.report_trade(order, "GOING NEUTRAL")
            self.position = 0
        if (
            self.prepared_data["position"].iloc[-1] == -1
        ):  # if position is short -> go/stay short
            if self.position == 0:
                order = client.futures_create_order(
                    symbol=self.symbol, side="SELL", type="MARKET", quantity=self.units
                )
                self.report_trade(order, "GOING SHORT")
            elif self.position == 1:
                order = client.futures_create_order(
                    symbol=self.symbol,
                    side="SELL",
                    type="MARKET",
                    quantity=2 * self.units,
                )
                self.report_trade(order, "GOING SHORT")
            self.position = -1

    def report_trade(self, order, going):
        time.sleep(0.1)
        order_time = order["updateTime"]
        trades = client.futures_account_trades(symbol=self.symbol, startTime=order_time)
        order_time = pd.to_datetime(order_time, unit="ms")

        # extract data from trades object
        df = pd.DataFrame(trades)
        columns = ["qty", "quoteQty", "commission", "realizedPnl"]
        for column in columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        base_units = round(df.qty.sum(), 5)
        quote_units = round(df.quoteQty.sum(), 5)
        commission = -round(df.commission.sum(), 5)
        real_profit = round(df.realizedPnl.sum(), 5)
        price = round(quote_units / base_units, 5)

        # calculate cumulative trading profits
        self.cum_profits += round((commission + real_profit), 5)

        # print trade report
        print(2 * "\n" + 100 * "-")
        print("{} | {}".format(order_time, going))
        print(
            "{} | Base_Units = {} | Quote_Units = {} | Price = {} ".format(
                order_time, base_units, quote_units, price
            )
        )
        print(
            "{} | Profit = {} | CumProfits = {} ".format(
                order_time, real_profit, self.cum_profits
            )
        )
        print(100 * "-" + "\n")
