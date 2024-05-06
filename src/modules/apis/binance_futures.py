import typing
import hashlib
import hmac
import json
import logging
from time import time
from urllib.parse import urlencode
import requests
import pprint
import threading

import websocket

# import modules
from modules.models import Balance, Candle, Contract, OrderStatus
from modules.strategies import BreakoutStrategy, TechnicalStrategy, VWAPStrategy
from modules.util import Request

logger = logging.getLogger()

live_url = "https://fapi.binance.com"  # live
testnet_url = "https://testnet.binancefuture.com"  # testnet

live_websocket_url = "wss://fstream.binance.com"  # live
testnet_websocket_url = "wss://stream.binancefuture.com/ws"  # testnet

ep_exchange_info = "/fapi/v1/exchangeInfo"
ep_klines = "/fapi/v1/klines"
ep_account = "/fapi/v1/account"
ep_order = "/fapi/v1/order"
ep_book_ticker = "/fapi/v1/ticker/bookTicker"


class BinanceFuturesClient:
    def __init__(self, public_key: str, secret_key: str, testnet: bool):
        if testnet:
            self._base_url = testnet_url
            self._wss_url = testnet_websocket_url
        else:
            self._base_url = live_url
            self._wss_url = live_websocket_url

        self._public_key = public_key
        self._secret_key = secret_key

        headers = {"X-MBX-APIKEY": self._public_key}

        self._request_handler = Request(self._base_url, headers=headers)

        self.contracts = self.get_contracts()
        self.balances = self.get_balances()

        self.prices = dict()
        self.strategies: typing.Dict[
            int, typing.Union[TechnicalStrategy, BreakoutStrategy, VWAPStrategy]
        ] = dict()

        self.logs = []

        self._ws_id = 1
        self._ws = None

        t = threading.Thread(target=self._start_ws)
        t.start()

        logger.info("Binance Futures Client successfully initialized")

    def _add_log(self, msg: str):
        logger.info(f"{msg}")
        self.logs.append({"log": msg, "displayed": False})

    def _generate_signature(self, data: typing.Dict) -> str:
        return hmac.new(
            self._secret_key.encode(), urlencode(data).encode(), hashlib.sha256
        ).hexdigest()

    def get_contracts(self) -> typing.Dict[str, Contract]:
        exchange_info = self._request_handler.GET(ep_exchange_info, None)
        contracts = dict()

        if exchange_info is not None:
            for contract in exchange_info["symbols"]:
                contracts[contract["symbol"]] = Contract(contract, "Binance")
        return contracts

    def get_historical_candles(
        self, contract: Contract, interval: str
    ) -> typing.List[Candle]:
        data = dict()
        data["symbol"] = contract.symbol
        data["interval"] = interval
        data["limit"] = 1000

        raw_candles = self._request_handler.GET(ep_klines, data)
        candles = []

        if raw_candles is not None:
            for c in raw_candles:
                candles.append(Candle(c))
        return candles

    def get_bid_ask(self, contract: Contract) -> typing.Dict[str, float]:
        data = dict()
        data["symbol"] = contract.symbol  # type: ignore
        order_book = self._request_handler.GET(ep_book_ticker, data)
        if order_book is not None:
            if contract.symbol not in self.prices:
                self.prices[contract.symbol] = {
                    "bid": float(order_book["bidPrice"]),
                    "ask": float(order_book["askPrice"]),
                }
            else:
                self.prices[contract.symbol]["bid"] = float(order_book("bidPrice"))
                self.prices[contract.symbol]["ask"] = float(order_book("askPrice"))

        return self.prices[contract.symbol]

    def get_balances(self) -> typing.Dict[str, Balance]:
        data = dict()
        data["timestamp"] = int(time() * 1000)
        data["signature"] = self._generate_signature(data)

        balances = dict()

        account_data = self._request_handler.GET(ep_account, data)

        if account_data is not None:
            for a in account_data["assets"]:
                balances[a["asset"]] = Balance(a)

        return balances

    def place_order(
        self,
        contract: Contract,
        order_type: str,
        quantity: float,
        side: str,
        price=None,
        tif=None,
    ) -> OrderStatus:
        data = dict()
        data["symbol"] = contract.symbol
        data["side"] = side
        data["quantity"] = round(
            round(quantity / contract.lot_size) * contract.lot_size, 8
        )
        data["type"] = order_type

        if price is not None:
            data["price"] = round(
                round(price / contract.tick_size) * contract.tick_size, 8
            )

        if tif is not None:
            data["timeInForce"] = tif

        data["timestamp"] = int(time() * 1000)
        data["signature"] = self._generate_signature(data)
        order_status = self._request_handler.POST(ep_order, data)

        if order_status is not None:
            order_status = OrderStatus(order_status)

        return order_status

    def cancel_order(self, contract: Contract, order_id: int) -> OrderStatus:
        data = dict()
        data["orderId"] = order_id
        data["symbol"] = contract.symbol

        data["timestamp"] = int(time() * 1000)
        data["signature"] = self._generate_signature(data)

        order_status = self._request_handler.DELETE(ep_order, data)

        if order_status is not None:
            order_status = OrderStatus(order_status)

        return order_status

    def get_order_status(self, contract: Contract, order_id: int) -> OrderStatus:
        data = dict()
        data["timestamp"] = int(time() * 1000)
        data["symbol"] = contract.symbol
        data["orderId"] = order_id
        data["signature"] = self._generate_signature(data)

        order_status = self._request_handler.GET(ep_order, data)

        if order_status is not None:
            order_status = OrderStatus(order_status)

        return order_status

    def _start_ws(self):
        self._ws = websocket.WebSocketApp(
            self._wss_url,
            on_open=self._on_open,
            on_close=self._on_close,
            on_error=self._on_error,
            on_message=self._on_message,
        )
        while True:
            try:
                self._ws.run_forever()
            except Exception as e:
                f"Binance error in run_forever() method: {e}"
            time.sleep(2)

    def _on_open(self, ws):
        logger.info("Binance websocket connection started")
        self.subscribe(list(self.contracts.values()), "bookTicker")

    def _on_close(self, ws):
        logger.warning("Binance websocket connection closed")

    def _on_error(self, ws, msg: str):
        logger.error(f"Binance connection error {msg}")

    def _on_message(self, ws, msg: str):
        data = json.loads(msg)

        if "e" in data:
            if data["e"] == "bookTicker":
                symbol = data["s"]

                if symbol not in self.prices:
                    self.prices[symbol] = {
                        "bid": float(data["b"]),
                        "ask": float(data["a"]),
                    }
                else:
                    self.prices[symbol]["bid"] = float(data["b"])
                    self.prices[symbol]["ask"] = float(data["a"])

                # PNL Calculation

                try:
                    for b_index, strat in self.strategies.items():
                        if strat.contract.symbol == symbol:
                            for trade in strat.trades:
                                if (
                                    trade.status == "open"
                                    and trade.entry_price is not None
                                ):
                                    if trade.side == "long":
                                        trade.pnl = (
                                            self.prices[symbol]["bid"]
                                            - trade.entry_price
                                        ) * trade.quantity
                                    elif trade.side == "short":
                                        trade.pnl = (
                                            trade.entry_price
                                            - self.prices[symbol]["ask"]
                                        ) * trade.quantity
                except RuntimeError as e:
                    logger.error(
                        "Error while looping through the Binance strategies: %s", e
                    )

            if data["e"] == "aggTrade":
                symbol = data["s"]

                for key, strat in self.strategies.items():
                    if strat.contract.symbol == symbol:
                        res = strat.parse_trades(
                            float(data["p"]), float(data["q"]), data["T"]
                        )
                        strat.check_trade(res)

    def subscribe(self, contracts: typing.List[Contract], channel: str):
        data = dict()
        data["method"] = "SUBSCRIBE"
        data["params"] = []

        for contract in contracts:
            data["params"].append(contract.symbol.lower() + "@" + channel)
        data["id"] = self._ws_id

        try:
            self._ws.send(json.dumps(data))
        except Exception as e:
            f"WebsocketError: Error while subscribing to {len(contracts)} {channel} updates: {e}"

        self._ws_id += 1

    def get_trade_size(self, contract: Contract, price: float, balance_pct: float):
        balance = self.get_balances()
        if balance is not None:
            if "USDT" in balance:
                balance = balance["USDT"].wallet_balance
            else:
                return None
        else:
            return None

        trade_size = (balance * balance_pct / 100) / price

        trade_size = round(round(trade_size / contract.lot_size) * contract.lot_size, 8)
        logger.info(
            "-" * 50
            + "\nBinance Futures\n"
            + "-" * 50
            + f"\nUSDT balance = {balance}\nTrade size = {trade_size}"
        )
        return trade_size
