import os
import csv
import json
import urllib.parse
import urllib.request

API_KEY = os.environ.get("FRED_API_KEY")

if not API_KEY:
    raise RuntimeError("FRED_API_KEY が設定されていません")


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


print("FREDデータ取得中...")

sp500 = get_series("SP500")
vix = get_series("VIXCLS")
hy = get_series("BAMLH0A0HYM2")

print("S&P500取得数:", len(sp500))
print("VIX取得数:", len(vix))
print("HY取得数:", len(hy))

sp500_dates = sorted(sp500.keys())

vix_aligned = build_aligned_series(
    vix,
    sp500_dates
)

hy_aligned = build_aligned_series(
    hy,
    sp500_dates
)

dates = [
    date
    for date in sp500_dates
    if date in vix_aligned
    and date in hy_aligned
]

print("計算可能な営業日:", len(dates))


# ==========================================
# 先に全営業日のスコアを作る
# ==========================================

daily_scores = {}

for i in range(200, len(dates)):

    date = dates[i]

    price = sp500[date]
    prev_price = sp500[dates[i - 1]]

    vix_now = vix_aligned[date]
    vix_prev = vix_aligned[dates[i - 1]]

    hy_now = hy_aligned[date]
    hy_prev = hy_aligned[dates[i - 1]]

    prices_200 = [
        sp500[dates[j]]
        for j in range(i - 199, i + 1)
    ]

    ma200 = sum(prices_200) / 200

    ma_diff = (
        (price / ma200) - 1
    ) * 100

    sp500_change = (
        (price / prev_price) - 1
    ) * 100

    vix_change = (
        (vix_now / vix_prev) - 1
    ) * 100

    hy_change = hy_now - hy_prev


    # Base Risk Score
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


    # Sudden Risk Score
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


    daily_scores[date] = {
        "base_score": base_score,
        "sudden_score": sudden_score
    }


# ==========================================
# バックテスト本体
# ==========================================

rows = []

for i in range(220, len(dates) - 20):

    date = dates[i]

    price = sp500[date]
    prev_price = sp500[dates[i - 1]]

    vix_now = vix_aligned[date]
    vix_prev = vix_aligned[dates[i - 1]]

    hy_now = hy_aligned[date]
    hy_prev = hy_aligned[dates[i - 1]]

    prices_200 = [
        sp500[dates[j]]
        for j in range(i - 199, i + 1)
    ]

    ma200 = sum(prices_200) / 200

    ma_diff = (
        (price / ma200) - 1
    ) * 100


    # 当日変化
    sp500_change = (
        (price / prev_price) - 1
    ) * 100

    vix_change = (
        (vix_now / vix_prev) - 1
    ) * 100

    hy_change = hy_now - hy_prev


    # ======================================
    # 5日・10日・20日変化
    # ======================================

    def pct_change(current, past):
        return ((current / past) - 1) * 100


    sp500_change_5d = pct_change(
        price,
        sp500[dates[i - 5]]
    )

    sp500_change_10d = pct_change(
        price,
        sp500[dates[i - 10]]
    )

    sp500_change_20d = pct_change(
        price,
        sp500[dates[i - 20]]
    )


    vix_change_5d = pct_change(
        vix_now,
        vix_aligned[dates[i - 5]]
    )

    vix_change_10d = pct_change(
        vix_now,
        vix_aligned[dates[i - 10]]
    )

    vix_change_20d = pct_change(
        vix_now,
        vix_aligned[dates[i - 20]]
    )


    hy_change_5d = (
        hy_now
        - hy_aligned[dates[i - 5]]
    )

    hy_change_10d = (
        hy_now
        - hy_aligned[dates[i - 10]]
    )

    hy_change_20d = (
        hy_now
        - hy_aligned[dates[i - 20]]
    )


    # ======================================
    # 当日のスコア
    # ======================================

    base_score = daily_scores[date]["base_score"]
    sudden_score = daily_scores[date]["sudden_score"]


    # ======================================
    # 直近20営業日の警戒記憶
    # ======================================

    recent_dates = dates[i - 19:i + 1]

    recent_base_scores = [
        daily_scores[d]["base_score"]
        for d in recent_dates
        if d in daily_scores
    ]

    recent_sudden_scores = [
        daily_scores[d]["sudden_score"]
        for d in recent_dates
        if d in daily_scores
    ]

    recent20_max_base = max(recent_base_scores)
    recent20_max_sudden = max(recent_sudden_scores)


    # 仮の「警戒記憶」判定
    memory_warning = 0

    if (
        recent20_max_base >= 3
        or recent20_max_sudden >= 2
    ):
        memory_warning = 1


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
        for j in range(i + 1, i + 21)
    ]

    min_future = min(future_prices)

    max_drawdown_20d = (
        (min_future / price) - 1
    ) * 100


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

        round(sp500_change_5d, 2),
        round(sp500_change_10d, 2),
        round(sp500_change_20d, 2),

        round(vix_change_5d, 2),
        round(vix_change_10d, 2),
        round(vix_change_20d, 2),

        round(hy_change_5d, 2),
        round(hy_change_10d, 2),
        round(hy_change_20d, 2),

        base_score,
        sudden_score,

        recent20_max_base,
        recent20_max_sudden,
        memory_warning,

        round(return_20d, 2),
        round(max_drawdown_20d, 2)
    ])


filename = "backtest_results_v11.csv"

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

        "sp500_change_5d",
        "sp500_change_10d",
        "sp500_change_20d",

        "vix_change_5d",
        "vix_change_10d",
        "vix_change_20d",

        "hy_change_5d_pt",
        "hy_change_10d_pt",
        "hy_change_20d_pt",

        "base_score",
        "sudden_score",

        "recent20_max_base",
        "recent20_max_sudden",
        "memory_warning",

        "return_20d",
        "max_drawdown_20d"
    ])

    writer.writerows(rows)


print("")
print("==========================")
print("v1.1 バックテスト完了")
print("==========================")
print("出力:", filename)
print("件数:", len(rows))