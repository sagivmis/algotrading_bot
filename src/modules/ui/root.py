import logging
import time
import tkinter as tk

from modules.ui.strategy import StrategyPanel
from modules.ui.trades import Trades

from ..apis.binance_futures import BinanceFuturesClient
from modules.ui.logging import Logging
from modules.ui.watchlist import Watchlist
from .styling import *

logger = logging.getLogger()


class Root(tk.Tk):
    def __init__(self, binance: BinanceFuturesClient):
        super().__init__()
        self.binance = binance
        self.bybit = binance

        self.title("Bali BOT")
        self.configure(bg=BG_COLOR)

        self._left_frame = tk.Frame(self, bg=BG_COLOR)
        self._left_frame.pack(side=tk.LEFT)
        self._right_frame = tk.Frame(self, bg=BG_COLOR)
        self._right_frame.pack(side=tk.RIGHT)

        self._watchlist_frame = Watchlist(
            self.binance.contracts, self.bybit.contracts, self._left_frame, bg=BG_COLOR
        )
        self._watchlist_frame.pack(side=tk.TOP)

        self.logging_frame = Logging(self._left_frame, bg=BG_COLOR)
        self.logging_frame.pack(side=tk.TOP)

        self._strategy_frame = StrategyPanel(self, binance=self.binance, bg=BG_COLOR)
        self._strategy_frame.pack(side=tk.TOP)

        self._trades_frame = Trades(self._right_frame, bg=BG_COLOR)
        self._trades_frame.pack(side=tk.TOP)

        self._update_ui()

    def _update_logging(self):
        for log in self.binance.logs:
            if not log["displayed"]:
                self.logging_frame.add_log(log["log"])
                log["displayed"] = True

    def _update_watchlist(self):
        try:
            for key, value in self._watchlist_frame.body_widgets["symbol"].items():
                symbol = self._watchlist_frame.body_widgets["symbol"][key].cget("text")
                exchange = self._watchlist_frame.body_widgets["exchange"][key].cget(
                    "text"
                )

                if exchange == "Binance":
                    if symbol not in self.binance.contracts:
                        continue
                    if symbol not in self.binance.prices:
                        self.binance.get_bid_ask(self.binance.contracts[symbol])
                        continue

                    precision = self.binance.contracts[symbol].price_decimals

                    prices = self.binance.prices[symbol]

                elif exchange == "Bybit":
                    if symbol not in self.bybit.contracts:
                        continue
                    if symbol not in self.bybit.prices:
                        self.bybit.get_bid_ask(self.bybit.contracts[symbol])
                        continue

                    precision = self.bybit.contracts[symbol].price_decimals
                    prices = self.bybit.prices[symbol]

                else:
                    continue

                if prices["bid"] is not None:
                    price_str = "{0:.{prec}f}".format(prices["bid"], prec=precision)
                    self._watchlist_frame.body_widgets["bid_var"][key].set(price_str)

                if prices["ask"] is not None:
                    price_str = "{0:.{prec}f}".format(prices["ask"], prec=precision)
                    self._watchlist_frame.body_widgets["ask_var"][key].set(price_str)
        except RuntimeError as e:
            logger.error(f"Error while looping through watchlist dictionary {e}")

    def _update_trades(self):
        for client in [self.binance]:
            try:
                for b_index, strat in client.strategies.items():
                    for log in strat.logs:
                        if not log["displayed"]:
                            self.logging_frame.add_log(log["log"])
                            log["displayed"] = True

                    for trade in strat.trades:
                        if trade.time not in self._trades_frame.body_widgets["symbol"]:
                            self._trades_frame.add_trade(trade)
                        if trade.contract.exchange == "binance":
                            precision = trade.contract.price_decimals

                        pnl_str = "0:.{prec}f}".format(trade.pnl, prec=precision)
                        self._trades_frame.body_widgets["pnl_var"][trade.time].set(
                            pnl_str
                        )
                        self._trades_frame.body_widgets["status_var"][trade.time].set(
                            trade.status.capitalize()
                        )

            except RuntimeError as e:
                logger.error(f"Error while looping through strategies dictionary: {e}")

    def _update_ui(self):
        # logs
        self._update_logging()

        # watchlist prices
        self._update_watchlist()

        # trades
        self._update_trades()

        self.after(1500, self._update_ui)
