"""Download the last 60 days of 5-minute futures data from Yahoo Finance into backtest/data/."""
import os
import yfinance as yf

os.makedirs("data", exist_ok=True)
for t in ["NQ=F", "ES=F", "YM=F", "RTY=F", "GC=F", "6E=F"]:
    d = yf.download(t, interval="5m", period="60d", progress=False)
    d.columns = [c[0] for c in d.columns]
    d.to_csv("data/%s.csv" % t.replace("=F", ""))
    print(t, d.shape, d.index[0], d.index[-1])
