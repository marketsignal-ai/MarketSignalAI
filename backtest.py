import os
import csv
import json
import urllib.parse
import urllib.request
from datetime import datetime

API_KEY = os.environ.get("FRED_API_KEY")

if not API_KEY:
    raise RuntimeError("FRED_API_KEY が設定されていません")


def get_series(series_id, limit=3000):
    params = urllib.parse.urlencode({
        "series_id": series_id,
        "api_key": API_KEY,
        "file_type": "json",
        "sort_order": "asc",
        "limit": limit
    })

    url = "https://api.stlouisfed.org/fred/series/observations?" + params

    with urllib.request.urlopen(url) as response:
        data = json.load(response)

    result = {}

    for obs in data.get("observations", []):
        value = obs.get("value")

        if value and value != ".":
            result[obs["date"]] = float(value)

    return result


print("FREDデータ取得中...")

sp500 = get_series("SP500")
vix = get_series("VIXCLS")
hy = get_series("BAMLH0A0HYM2")


# 共通して存在する日付だけ使う
dates = sorted(
    set(sp500.keys())
    & set(vix.keys())
    & set(hy.keys())
)


rows = []

for i in range(200, len(dates) - 20):

    date = dates[i]

    price = sp500[date]
    prev_price = sp500[dates[i - 1]]

    vix_now = vix[date]
    vix_prev = vix[dates[i - 1]]

    hy_now = hy[date]
    hy_prev = hy[dates[i - 1]]

    # 200日移動平均
    prices_200 = [
        sp500[dates[j]]
        for j in range(i - 199, i + 1)
    ]

    ma200 = sum(prices_200) / 200

    ma_diff = ((price / ma200) - 1) * 100

    # 前日変化
    sp500_change = ((price / prev_price) - 1) * 100
    vix_change = ((vix_now / vix_prev) - 1) * 100
    hy_change = hy_now - hy_prev


    # =========================
    # Base Risk Score
    # =========================

    base_score = 0

    if vix_now >= 30:
        base_score += 3
    elif vix_now >= 25:
        base_score += 2
    elif vix_now >= 20:
        base_score += 1


    if ma_diff <= -10:
        base_score += 3
    elif ma_diff <= -5:
        base_score += 2
    elif ma_diff < 0:
        base_score += 1


    if hy_now >= 6:
        base_score += 3
    elif hy_now >= 5:
        base_score += 2
    elif hy_now >= 4:
        base_score += 1


    # =========================
    # Sudden Risk Score
    # =========================

    sudden_score = 0

    if sp500_change <= -3:
        sudden_score += 2
    elif sp500_change <= -2:
        sudden_score += 1


    if vix_change >= 30:
        sudden_score += 2
    elif vix_change >= 15:
        sudden_score += 1


    if hy_change >= 0.50:
        sudden_score += 2
    elif hy_change >= 0.25:
        sudden_score += 1


    # =========================
    # 20営業日後
    # =========================

    future_price = sp500[dates[i + 20]]

    return_20d = ((future_price / price) - 1) * 100


    # 20営業日以内の最大下落
    future_prices = [
        sp500[dates[j]]
        for j in range(i + 1, i + 21)
    ]

    min_future = min(future_prices)

    max_drawdown_20d = ((min_future / price) - 1) * 100


    rows.append([
        date,
        round(price, 2),
        round(vix_now, 2),
        round(hy_now, 2),
        round(ma200, 2),
        round(ma_diff, 2),
        round(sp500_change, 2),
        round(vix_change, 2),
        round(hy_change, 2),
        base_score,
        sudden_score,
        round(return_20d, 2),
        round(max_drawdown_20d, 2)
    ])


filename = "backtest_results.csv"

with open(filename, "w", newline="", encoding="utf-8-sig") as f:

    writer = csv.writer(f)

    writer.writerow([
        "date",
        "sp500",
        "vix",
        "high_yield_spread",
        "sp500_200ma",
        "sp500_200ma_diff",
        "sp500_daily_change",
        "vix_daily_change",
        "high_yield_daily_change",
        "base_score",
        "sudden_score",
        "return_20d",
        "max_drawdown_20d"
    ])

    writer.writerows(rows)


print("バックテスト完了")
print("出力:", filename)
print("件数:", len(rows))