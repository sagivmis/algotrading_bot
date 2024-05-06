from modules import BinanceFuturesClient
import tkinter as tk
import logging

from modules.ui.root import Root

# INIT
api_key = "876a0aa7f6e9c11b363a666902b0668407ee313f52396c22d85800b2c8b4f3f6"
secret_key = "9473252093d4895607c2fde6a3efe81b81d966c3597c5ca61caf9d3288f271f1"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s %(levelname)s\t :: %(message)s")

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler("info.log")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

logger.addHandler(stream_handler)
logger.addHandler(file_handler)

if __name__ == "__main__":
    # binance_contracts = get_contract()
    # client = Client(api_key=api_key, api_secret=secret_key, tld="com", testnet=True)
    binance = BinanceFuturesClient(
        public_key=api_key, secret_key=secret_key, testnet=True
    )

    root = Root(binance)

    root.mainloop()

    # symbol = "BTCUSDT"
    # bar_length = "1m"
    # sma_s = 10
    # sma_m = 20
    # sma_l = 50
    # units = 0.001
    # position = 0
    # leverage = 10

    # trader = Trader(symbol=symbol, bar_length=bar_length,
    #                        sma_s=sma_s, sma_m=sma_m, sma_l=sma_l,
    #                        units=units, position=position, leverage=leverage)

    # trader.start_trading(historical_days=1 / 24)
