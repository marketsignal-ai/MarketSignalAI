import os
import csv
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
            f"{ticker} の取得に失敗しました"
        )

    if isinstance(df.columns, pd.MultiIndex):
        close = df["Close"][ticker]
    else:
        close = df["Close"]

    result = {}

    for date, value in close.items():

        if pd.notna(value):

            result[
                date.strftime("%Y-%m-%d")
            ] = float(value)

    return result


# ==========================================
# FRED
# ==========================================

def get_fred_series(series_id, start_date):

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

    with urllib.request.urlopen(url) as response:
        data = json.load(response)

    result = {}

    for obs in data.get(
        "observations",
        []
    ):

        value = obs.get("value")

        if value and value != ".":
            result[
                obs["date"]
            ] = float(value)

    return result


# ==========================================
# 営業日に合わせる
# ==========================================

def align_series(
    source,
    target_dates
):

    result = {}

    source_dates = sorted(
        source.keys()
    )

    j = 0
    latest = None

    for date in target_dates:

        while (
            j < len(source_dates)
            and source_dates[j] <= date
        ):

            latest = source[
                source_dates[j]
            ]

            j += 1

        if latest is not None:
            result[date] = latest

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


print("")
print("==========================")
print("取得結果")
print("==========================")

print("S&P500:", len(sp500))
print("VIX:", len(vix))
print("BAA10Y:", len(baa10y))


# ==========================================
# S&P500営業日基準
# ==========================================

dates = sorted(
    sp500.keys()
)

vix_aligned = align_series(
    vix,
    dates
)

baa_aligned = align_series(
    baa10y,
    dates
)


dates = [
    date
    for date in dates
    if date in vix_aligned
    and date in baa_aligned
]


print(
    "計算可能営業日:",
    len(dates)
)


# ==========================================
# 計算補助
# ==========================================

def pct_change(
    current,
    past
):

    return (
        (current / past) - 1
    ) * 100


# ==========================================
# 全期間バックテスト
# ==========================================

rows = []

# 200日線 + 60日未来を見るので
# 最初200日、最後60日は除外
for i in range(
    200,
    len(dates) - 60
):

    date = dates[i]

    price = sp500[date]
    vix_now = vix_aligned[date]
    baa_now = baa_aligned[date]


    # ======================================
    # 200日移動平均
    # ======================================

    prices_200 = [
        sp500[dates[j]]
        for j in range(
            i - 199,
            i + 1
        )
    ]

    ma200 = (
        sum(prices_200)
        / 200
    )

    ma_diff = (
        (price / ma200) - 1
    ) * 100


    # ======================================
    # S&P500変化
    # ======================================

    sp500_1d = pct_change(
        price,
        sp500[dates[i - 1]]
    )

    sp500_5d = pct_change(
        price,
        sp500[dates[i - 5]]
    )

    sp500_10d = pct_change(
        price,
        sp500[dates[i - 10]]
    )

    sp500_20d = pct_change(
        price,
        sp500[dates[i - 20]]
    )


    # ======================================
    # VIX変化
    # ======================================

    vix_1d = pct_change(
        vix_now,
        vix_aligned[
            dates[i - 1]
        ]
    )

    vix_5d = pct_change(
        vix_now,
        vix_aligned[
            dates[i - 5]
        ]
    )

    vix_10d = pct_change(
        vix_now,
        vix_aligned[
            dates[i - 10]
        ]
    )

    vix_20d = pct_change(
        vix_now,
        vix_aligned[
            dates[i - 20]
        ]
    )


    # ======================================
    # BAA10Y変化
    # 単位はpercentage point
    # ======================================

    baa_1d = (
        baa_now
        - baa_aligned[
            dates[i - 1]
        ]
    )

    baa_5d = (
        baa_now
        - baa_aligned[
            dates[i - 5]
        ]
    )

    baa_10d = (
        baa_now
        - baa_aligned[
            dates[i - 10]
        ]
    )

    baa_20d = (
        baa_now
        - baa_aligned[
            dates[i - 20]
        ]
    )


    # ======================================
    # 20営業日後
    # ======================================

    price_20 = sp500[
        dates[i + 20]
    ]

    return_20d = pct_change(
        price_20,
        price
    )

    future_20 = [
        sp500[dates[j]]
        for j in range(
            i + 1,
            i + 21
        )
    ]

    min_20 = min(
        future_20
    )

    max_drawdown_20d = (
        (min_20 / price) - 1
    ) * 100


    # ======================================
    # 60営業日後
    # ======================================

    price_60 = sp500[
        dates[i + 60]
    ]

    return_60d = pct_change(
        price_60,
        price
    )

    future_60 = [
        sp500[dates[j]]
        for j in range(
            i + 1,
            i + 61
        )
    ]

    min_60 = min(
        future_60
    )

    max_drawdown_60d = (
        (min_60 / price) - 1
    ) * 100


    # ======================================
    # CSV行
    # ======================================

    rows.append([
        date,

        round(price, 2),

        round(ma200, 2),
        round(ma_diff, 2),

        round(vix_now, 2),

        round(baa_now, 2),

        round(sp500_1d, 2),
        round(sp500_5d, 2),
        round(sp500_10d, 2),
        round(sp500_20d, 2),

        round(vix_1d, 2),
        round(vix_5d, 2),
        round(vix_10d, 2),
        round(vix_20d, 2),

        round(baa_1d, 3),
        round(baa_5d, 3),
        round(baa_10d, 3),
        round(baa_20d, 3),

        round(return_20d, 2),
        round(max_drawdown_20d, 2),

        round(return_60d, 2),
        round(max_drawdown_60d, 2)
    ])


# ==========================================
# CSV 1
# 全期間
# ==========================================

filename = (
    "long_backtest_results.csv"
)


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

        "sp500_200ma",
        "sp500_200ma_diff",

        "vix",

        "baa10y",

        "sp500_change_1d",
        "sp500_change_5d",
        "sp500_change_10d",
        "sp500_change_20d",

        "vix_change_1d",
        "vix_change_5d",
        "vix_change_10d",
        "vix_change_20d",

        "baa_change_1d_pt",
        "baa_change_5d_pt",
        "baa_change_10d_pt",
        "baa_change_20d_pt",

        "return_20d",
        "max_drawdown_20d",

        "return_60d",
        "max_drawdown_60d"
    ])

    writer.writerows(rows)


# ==========================================
# 危機一覧
# ==========================================

crises = {

    "1997 アジア通貨危機":
        "1997-07-02",

    "1998 LTCM・ロシア危機":
        "1998-08-17",

    "2000 ITバブル崩壊":
        "2000-03-24",

    "2008 リーマンショック":
        "2008-09-15",

    "2010 ギリシャ危機":
        "2010-04-27",

    "2011 欧州債務危機":
        "2011-08-05",

    "2015 中国ショック":
        "2015-08-24",

    "2018 年末急落":
        "2018-10-10",

    "2020 コロナショック":
        "2020-02-24",

    "2022 インフレ・利上げ":
        "2022-01-03",

    "2023 米地銀危機":
        "2023-03-10",

    "2025 関税ショック":
        "2025-04-02"
}


# ==========================================
# バックテスト行を辞書化
# ==========================================

header = [
    "date",

    "sp500",

    "sp500_200ma",
    "sp500_200ma_diff",

    "vix",

    "baa10y",

    "sp500_change_1d",
    "sp500_change_5d",
    "sp500_change_10d",
    "sp500_change_20d",

    "vix_change_1d",
    "vix_change_5d",
    "vix_change_10d",
    "vix_change_20d",

    "baa_change_1d_pt",
    "baa_change_5d_pt",
    "baa_change_10d_pt",
    "baa_change_20d_pt",

    "return_20d",
    "max_drawdown_20d",

    "return_60d",
    "max_drawdown_60d"
]


row_dict = {
    row[0]: dict(
        zip(
            header,
            row
        )
    )
    for row in rows
}


available_dates = sorted(
    row_dict.keys()
)


# ==========================================
# 指定日以前の営業日を探す
# ==========================================

def find_index_on_or_before(
    target_date
):

    valid = [
        i
        for i, d in enumerate(
            available_dates
        )
        if d <= target_date
    ]

    if not valid:
        return None

    return valid[-1]


# ==========================================
# CSV 2
# 危機前スナップショット
# ==========================================

crisis_rows = []

offsets = [
    60,
    30,
    20,
    10,
    5,
    0
]


for crisis_name, crisis_date in (
    crises.items()
):

    crisis_index = (
        find_index_on_or_before(
            crisis_date
        )
    )

    if crisis_index is None:
        continue


    for offset in offsets:

        index = (
            crisis_index
            - offset
        )

        if index < 0:
            continue

        date = available_dates[
            index
        ]

        data = row_dict[
            date
        ]


        crisis_rows.append([
            crisis_name,
            crisis_date,

            -offset,

            date,

            data["sp500"],

            data[
                "sp500_200ma_diff"
            ],

            data["vix"],

            data["baa10y"],

            data[
                "sp500_change_20d"
            ],

            data[
                "vix_change_20d"
            ],

            data[
                "baa_change_20d_pt"
            ],

            data[
                "max_drawdown_20d"
            ],

            data[
                "max_drawdown_60d"
            ]
        ])


crisis_filename = (
    "crisis_snapshots.csv"
)


with open(
    crisis_filename,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "crisis",
        "crisis_reference_date",

        "trading_days_before",

        "snapshot_date",

        "sp500",

        "sp500_200ma_diff",

        "vix",

        "baa10y",

        "sp500_change_20d",

        "vix_change_20d",

        "baa_change_20d_pt",

        "future_max_drawdown_20d",

        "future_max_drawdown_60d"
    ])

    writer.writerows(
        crisis_rows
    )


print("")
print("==========================")
print("長期バックテスト完了")
print("==========================")

print(
    "全期間CSV:",
    filename
)

print(
    "件数:",
    len(rows)
)

print(
    "危機分析CSV:",
    crisis_filename
)

print(
    "危機スナップショット件数:",
    len(crisis_rows)
)