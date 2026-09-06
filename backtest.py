import os
import json
import urllib.parse
import urllib.request

import pandas as pd
import yfinance as yf


API_KEY = os.environ.get("FRED_API_KEY")

if not API_KEY:
    raise RuntimeError("FRED_API_KEY が設定されていません")


START_DATE = "1990-01-01"


# ==========================================
# Yahoo Finance
# ==========================================

def get_yahoo_series(ticker, start_date):

    print(f"Yahoo取得中: {ticker}")

    df = yf.download(
        ticker,
        start=start_date,
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False
    )

    if df.empty:
        raise RuntimeError(
            f"{ticker} のデータ取得に失敗しました"
        )

    # yfinanceのバージョンによって
    # MultiIndexになる場合への対応
    if isinstance(df.columns, pd.MultiIndex):
        close = df["Close"][ticker]
    else:
        close = df["Close"]

    result = {}

    for date, value in close.items():

        if pd.notna(value):

            date_str = date.strftime(
                "%Y-%m-%d"
            )

            result[date_str] = float(value)

    return result


# ==========================================
# FRED
# ==========================================

def get_fred_series(
    series_id,
    start_date
):

    print(f"FRED取得中: {series_id}")

    params = urllib.parse.urlencode({
        "series_id": series_id,
        "api_key": API_KEY,
        "file_type": "json",
        "observation_start": start_date,
        "sort_order": "asc",
        "limit": 100000
    })

    url = (
        "https://api.stlouisfed.org/"
        "fred/series/observations?"
        + params
    )

    with urllib.request.urlopen(
        url
    ) as response:

        data = json.load(response)

    result = {}

    for obs in data.get(
        "observations",
        []
    ):

        value = obs.get("value")

        if (
            value
            and value != "."
        ):

            result[
                obs["date"]
            ] = float(value)

    return result


# ==========================================
# データ取得
# ==========================================

sp500 = get_yahoo_series(
    "^GSPC",
    START_DATE
)

vix = get_yahoo_series(
    "^VIX",
    START_DATE
)

baa10y = get_fred_series(
    "BAA10Y",
    START_DATE
)


# ==========================================
# 取得結果
# ==========================================

print("")
print("==========================")
print("長期データ取得結果")
print("==========================")

print(
    "S&P500:",
    len(sp500),
    min(sp500.keys()),
    "～",
    max(sp500.keys())
)

print(
    "VIX:",
    len(vix),
    min(vix.keys()),
    "～",
    max(vix.keys())
)

print(
    "BAA10Y:",
    len(baa10y),
    min(baa10y.keys()),
    "～",
    max(baa10y.keys())
)


# ==========================================
# 共通期間確認
# ==========================================

common_start = max(
    min(sp500.keys()),
    min(vix.keys()),
    min(baa10y.keys())
)

common_end = min(
    max(sp500.keys()),
    max(vix.keys()),
    max(baa10y.keys())
)

print("")
print(
    "共通バックテスト期間:",
    common_start,
    "～",
    common_end
)

print("")
print("==========================")
print("確認したい危機")
print("==========================")

crises = {
    "1997 アジア通貨危機":
        "1997-07-01",

    "1998 LTCM・ロシア危機":
        "1998-08-01",

    "2000 ITバブル崩壊":
        "2000-03-01",

    "2008 リーマンショック":
        "2008-09-01",

    "2010 ギリシャ危機":
        "2010-04-01",

    "2011 欧州債務危機":
        "2011-07-01",

    "2015 中国ショック":
        "2015-08-01",

    "2018 年末急落":
        "2018-10-01",

    "2020 コロナショック":
        "2020-02-01",

    "2022 インフレ・利上げ":
        "2022-01-01",

    "2023 米地銀危機":
        "2023-03-01",

    "2025 関税ショック":
        "2025-02-01"
}


for name, date in crises.items():

    if (
        common_start
        <= date
        <= common_end
    ):

        print(
            "OK ",
            name
        )

    else:

        print(
            "NG ",
            name
        )