from datetime import datetime
import tkinter as tk
import typing

from modules.models import *
from .styling import *

from modules.apis.binance_futures import BinanceFuturesClient


class Trades(tk.Frame):
    def __init__(self, binance: BinanceFuturesClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.binance = binance
        self.bybit = binance
        self.body_widgets = dict()
        self._body_index = 1
        self._headers = [
            "time",
            "symbol",
            "exchange",
            "strategy",
            "side",
            "quantity",
            "status",
            "pnl",
        ]

        self._table_frame = tk.Frame(self, bg=BG_COLOR)
        self._table_frame.pack(side=tk.TOP)

        for idx, h in enumerate(self._headers):
            header = tk.Label(
                self._table_frame,
                text=h.capitalize() if h != "remove" else "",
                bg=BG_COLOR,
                fg=FG_COLOR,
                font=GLOBAL_BOLD_FONT,
            )
            header.grid(row=0, column=idx)

        for h in self._headers:
            self.body_widgets[h] = dict()
            if h in ["status", "pnl"]:
                self.body_widgets[h + "_var"] = dict()

    def add_trade(
        self,
        trade: Trade,
    ):
        b_index = self._body_index
        t_index = trade.time

        date_str = datetime.datetime.fromtimestamp(trade.time / 1000).strftime(
            "%b %d %H:%M"
        )

        self.body_widgets["time"][t_index] = tk.Label(
            self._table_frame,
            text=date_str,
            bg=BG_COLOR,
            fg=FG_COLOR_2,
            font=GLOBAL_FONT,
        )
        self.body_widgets["time"][t_index].grid(row=b_index, column=0)

        self.body_widgets["symbol"][t_index] = tk.Label(
            self._table_frame,
            text=trade.contract.symbol,
            bg=BG_COLOR,
            fg=FG_COLOR_2,
            font=GLOBAL_FONT,
        )
        self.body_widgets["symbol"][t_index].grid(row=b_index, column=1)

        self.body_widgets["exchange"][t_index] = tk.Label(
            self._table_frame,
            text=trade.contract.exchange.capitalize(),
            bg=BG_COLOR,
            fg=FG_COLOR_2,
            font=GLOBAL_FONT,
        )
        self.body_widgets["exchange"][t_index].grid(row=b_index, column=2)

        self.body_widgets["strategy"][t_index] = tk.Label(
            self._table_frame,
            text=trade.strategy,
            bg=BG_COLOR,
            fg=FG_COLOR_2,
            font=GLOBAL_FONT,
        )
        self.body_widgets["strategy"][t_index].grid(row=b_index, column=3)

        self.body_widgets["side"][t_index] = tk.Label(
            self._table_frame,
            text=trade.side.capitalize(),
            bg=BG_COLOR,
            fg=FG_COLOR_2,
            font=GLOBAL_FONT,
        )
        self.body_widgets["side"][t_index].grid(row=b_index, column=4)

        self.body_widgets["quantity"][t_index] = tk.Label(
            self._table_frame,
            text=trade.quantity,
            bg=BG_COLOR,
            fg=FG_COLOR_2,
            font=GLOBAL_FONT,
        )
        self.body_widgets["quantity"][t_index].grid(row=b_index, column=5)

        self.body_widgets["status_var"][t_index] = tk.StringVar()
        self.body_widgets["status"][t_index] = tk.Label(
            self._table_frame,
            textvariable=self.body_widgets["status_var"][t_index],
            bg=BG_COLOR,
            fg=FG_COLOR_2,
            font=GLOBAL_FONT,
        )
        self.body_widgets["status"][t_index].grid(row=b_index, column=6)

        self.body_widgets["pnl_var"][t_index] = tk.StringVar()
        self.body_widgets["pnl"][t_index] = tk.Label(
            self._table_frame,
            textvariable=self.body_widgets["pnl_var"][t_index],
            bg=BG_COLOR,
            fg=FG_COLOR_2,
            font=GLOBAL_FONT,
        )
        self.body_widgets["pnl"][t_index].grid(row=b_index, column=7)

        self._body_index += 1
