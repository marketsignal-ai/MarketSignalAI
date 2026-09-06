import os
import csv
import json
import urllib.parse
import urllib.request

API_KEY = os.environ.get("FRED_API_KEY")

if not API_KEY:
    raise RuntimeError("FRED_API_KEY が設定されていません")


# ==========================================
# FREDからデータ取得
# ==========================================

def get_series(series_id, start_date="2016-01-01"):

    params = urllib.parse.urlencode({
        "series_id": series_id,
        "api_key": API_KEY,
        "file_type": "json",
        "observation_start": start_date,
        "sort_order": "asc",
        "limit": 100000
    })

    url = (
        "https://api.stlouisfed.org/fred/series/observations?"
        + params
    )

    with urllib.request.urlopen(url) as response:
        data = json.load(response)

    result = {}

    for obs in data.get("observations", []):

        value = obs.get("value")

        if value and value != ".":
            result[obs["date"]] = float(value)

    return result


print("FREDデータ取得中...")


# ==========================================
# データ取得
# ==========================================

sp500 = get_series("SP500")
vix = get_series("VIXCLS")
hy = get_series("BAMLH0A0HYM2")


print("S&P500取得数:", len(sp500))
print("VIX取得数:", len(vix))
print("HY取得数:", len(hy))


# ==========================================
# S&P500営業日を基準にする
# ==========================================

sp500_dates = sorted(sp500.keys())


# ==========================================
# 過去の最新値を探す
# ==========================================

def build_aligned_series(source, target_dates):

    result = {}

    source_dates = sorted(source.keys())

    j = 0
    latest_value = None

    for date in target_dates:

        while (
            j < len(source_dates)
            and source_dates[j] <= date
        ):

            latest_value = source[source_dates[j]]
            j += 1

        if latest_value is not None:
            result[date] = latest_value

    return result


vix_aligned = build_aligned_series(
    vix,
    sp500_dates
)

hy_aligned = build_aligned_series(
    hy,
    sp500_dates
)


# ==========================================
# 全データが存在する日付
# ==========================================

dates = [
    date
    for date in sp500_dates
    if date in vix_aligned
    and date in hy_aligned
]


print("計算可能な営業日:", len(dates))


# ==========================================
# バックテスト
# ==========================================

rows = []


for i in range(200, len(dates) - 20):

    date = dates[i]

    price = sp500[date]
    prev_price = sp500[dates[i - 1]]

    vix_now = vix_aligned[date]
    vix_prev = vix_aligned[dates[i - 1]]

    hy_now = hy_aligned[date]
    hy_prev = hy_aligned[dates[i - 1]]


    # ======================================
    # 200日移動平均
    # ======================================

    prices_200 = [
        sp500[dates[j]]
        for j in range(i - 199, i + 1)
    ]

    ma200 = sum(prices_200) / 200

    ma_diff = (
        (price / ma200) - 1
    ) * 100


    # ======================================
    # 前日変化
    # ======================================

    sp500_change = (
        (price / prev_price) - 1
    ) * 100

    vix_change = (
        (vix_now / vix_prev) - 1
    ) * 100

    # HYは「％変化」ではなくポイント差
    hy_change = (
        hy_now - hy_prev
    )


    # ======================================
    # Base Risk Score
    # ======================================

    base_score = 0


    # VIX

    if vix_now >= 30:

        base_score += 3

    elif vix_now >= 25:

        base_score += 2

    elif vix_now >= 20:

        base_score += 1


    # S&P500 vs 200日線

    if ma_diff <= -10:

        base_score += 3

    elif ma_diff <= -5:

        base_score += 2

    elif ma_diff < 0:

        base_score += 1


    # HYスプレッド

    if hy_now >= 6:

        base_score += 3

    elif hy_now >= 5:

        base_score += 2

    elif hy_now >= 4:

        base_score += 1


    # ======================================
    # Sudden Risk Score
    # ======================================

    sudden_score = 0


    # S&P500急落

    if sp500_change <= -3:

        sudden_score += 2

    elif sp500_change <= -2:

        sudden_score += 1


    # VIX急騰

    if vix_change >= 30:

        sudden_score += 2

    elif vix_change >= 15:

        sudden_score += 1


    # HY急拡大

    if hy_change >= 0.50:

        sudden_score += 2

    elif hy_change >= 0.25:

        sudden_score += 1


    # ======================================
    # 20営業日後リターン
    # ======================================

    future_price = sp500[
        dates[i + 20]
    ]

    return_20d = (
        (future_price / price) - 1
    ) * 100


    # ======================================
    # 20営業日以内の最大下落
    # ======================================

    future_prices = [
        sp500[dates[j]]
        for j in range(
            i + 1,
            i + 21
        )
    ]

    min_future = min(
        future_prices
    )

    max_drawdown_20d = (
        (min_future / price) - 1
    ) * 100


    # ======================================
    # 結果保存
    # ======================================

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


# ==========================================
# CSV出力
# ==========================================

filename = "backtest_results.csv"


with open(
    filename,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

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
        "high_yield_daily_change_pt",
        "base_score",
        "sudden_score",
        "return_20d",
        "max_drawdown_20d"
    ])

    writer.writerows(rows)


print("")
print("==========================")
print("バックテスト完了")
print("==========================")
print("出力:", filename)
print("件数:", len(rows))