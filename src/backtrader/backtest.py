from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os
import sys
from datetime import datetime

import pandas as pd
import pandas_ta as ta
import backtrader as bt

class VWAP(bt.Indicator):
    lines = ('vwap',)
    params = ()
    def __init__(self):
        pass
        

    def next(self):
        print(self.data)
        print(self.data.volume)
        print(self.data.high)

        avg_price = (self.data.high[0] + self.data.low[0] + self.data.close[0]) / 3
        self.l.vwap[0] = (self.data.volume * avg_price).cumsum() / self.data.volume.cumsum()


class TestStrategy(bt.Strategy):
    params = (
        # ('emaperiod', 100),
    )

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        current_price = self.datas[0]
        self.dataclose = current_price.close
        self.ema = bt.indicators.ExponentialMovingAverage(period= 100)
        self.vwap = VWAP()

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log(f'Close, %.2f' % self.dataclose[0])
        self.log(f'EMA, %.2f' % self.ema[0])
        self.log(f'VWAP, %.2f' % self.vwap[0])
        if self.datas[0].close[0] > self.vwap[len(self)-1]:  # Accessing corresponding VWAP value
            print('Close is above VWAP:', self.datas[0].close[0])

def backtrader_data_to_df(data):
    return pd.DataFrame({
        'Open': data.open.array,
        'High': data.high.array,
        'Low': data.low.array,
        'Close': data.close.array,
        'Volume': data.volume.array
    })

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(1000.0)
    cerebro.addstrategy(TestStrategy)

    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, './BTC.CSV')
    
    data  = bt.feeds.GenericCSVData(dtformat= lambda x: datetime.utcfromtimestamp(int(x) / 1000),
                                    dataname=datapath,
                                    datetime=0,
                                    high=2,
                                    low=3,
                                    open=1,
                                    close=4,
                                    volume=5,
                                    openinterest=-1)
    df = backtrader_data_to_df(data)
    # df['VWAP'] = ta.vwap(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'])
    cerebro.adddata(data)
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.run()

    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
