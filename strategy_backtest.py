import csv


INPUT_FILE = "long_backtest_results.csv"

INITIAL_MONEY = 1_000_000

# 売買タイムラグ
TRADE_DELAY = 1

# 仮の判定値
SELL_THRESHOLD = 4
RECOVERY_THRESHOLD = 4


# ==========================================
# CSV読み込み
# ==========================================

rows = []

with open(
    INPUT_FILE,
    "r",
    encoding="utf-8-sig"
) as f:

    reader = csv.DictReader(f)

    for row in reader:

        data = {}

        for key, value in row.items():

            if key == "date":
                data[key] = value
            else:
                data[key] = float(value)

        rows.append(data)


print("データ件数:", len(rows))


# ==========================================
# スコア計算
# ==========================================

def calculate_sell_score(row):

    score = 0

    # 信用市場悪化
    if row["baa_change_20d_pt"] >= 0.05:
        score += 1

    if row["baa_change_20d_pt"] >= 0.20:
        score += 1


    # VIX悪化
    if row["vix_change_20d"] >= 30:
        score += 1

    if row["vix_change_20d"] >= 60:
        score += 1


    # 株価下落
    if row["sp500_change_20d"] <= -2:
        score += 1

    if row["sp500_change_20d"] <= -5:
        score += 1


    # 長期トレンド
    if row["sp500_200ma_diff"] < 0:
        score += 1


    return score


def calculate_recovery_score(row):

    score = 0

    # VIXピークアウト
    if row["vix_change_5d"] < 0:
        score += 1

    if row["vix_change_10d"] < 0:
        score += 1


    # 信用スプレッド改善
    if row["baa_change_5d_pt"] < 0:
        score += 1

    if row["baa_change_10d_pt"] < 0:
        score += 1


    # 株価反発
    if row["sp500_change_5d"] > 0:
        score += 1

    if row["sp500_change_10d"] > 0:
        score += 1


    return score


for row in rows:

    row["sell_score"] = (
        calculate_sell_score(row)
    )

    row["recovery_score"] = (
        calculate_recovery_score(row)
    )


# ==========================================
# Buy & Hold
# ==========================================

start_price = rows[0]["sp500"]
end_price = rows[-1]["sp500"]

buy_hold_final = (
    INITIAL_MONEY
    * end_price
    / start_price
)


# ==========================================
# Market Signal AI戦略
# ==========================================

cash = 0
shares = INITIAL_MONEY / start_price

invested = True

pending_sell = None
pending_buy = None

trades = []


for i in range(len(rows)):

    row = rows[i]

    price = row["sp500"]


    # ======================================
    # 売却実行
    # ======================================

    if (
        pending_sell is not None
        and i >= pending_sell
        and invested
    ):

        cash = shares * price
        shares = 0

        invested = False
        pending_sell = None

        trades.append({
            "date": row["date"],
            "action": "SELL",
            "price": price,
            "sell_score": row["sell_score"],
            "recovery_score":
                row["recovery_score"]
        })


    # ======================================
    # 買い戻し実行
    # ======================================

    if (
        pending_buy is not None
        and i >= pending_buy
        and not invested
    ):

        shares = cash / price
        cash = 0

        invested = True
        pending_buy = None

        trades.append({
            "date": row["date"],
            "action": "BUY",
            "price": price,
            "sell_score": row["sell_score"],
            "recovery_score":
                row["recovery_score"]
        })


    # ======================================
    # シグナル判定
    # ======================================

    if invested:

        if (
            row["sell_score"]
            >= SELL_THRESHOLD
            and pending_sell is None
        ):

            pending_sell = (
                i + TRADE_DELAY
            )


    else:

        if (
            row["recovery_score"]
            >= RECOVERY_THRESHOLD
            and pending_buy is None
        ):

            pending_buy = (
                i + TRADE_DELAY
            )


# ==========================================
# 最終資産
# ==========================================

if invested:
    strategy_final = (
        shares
        * rows[-1]["sp500"]
    )
else:
    strategy_final = cash


# ==========================================
# 年率リターン
# ==========================================

years = (
    len(rows)
    / 252
)

buy_hold_cagr = (
    (buy_hold_final / INITIAL_MONEY)
    ** (1 / years)
    - 1
) * 100

strategy_cagr = (
    (strategy_final / INITIAL_MONEY)
    ** (1 / years)
    - 1
) * 100


# ==========================================
# 売買履歴CSV
# ==========================================

with open(
    "strategy_trades.csv",
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "date",
        "action",
        "sp500",
        "sell_score",
        "recovery_score"
    ])

    for trade in trades:

        writer.writerow([
            trade["date"],
            trade["action"],
            round(
                trade["price"],
                2
            ),
            trade["sell_score"],
            trade["recovery_score"]
        ])


# ==========================================
# 結果
# ==========================================

print("")
print("==============================")
print("Buy & Hold vs Market Signal AI")
print("==============================")

print("")
print("初期資産:")
print(
    f"{INITIAL_MONEY:,.0f} 円"
)

print("")
print("Buy & Hold 最終資産:")
print(
    f"{buy_hold_final:,.0f} 円"
)

print(
    "Buy & Hold CAGR:",
    f"{buy_hold_cagr:.2f}%"
)

print("")
print("Market Signal AI 最終資産:")
print(
    f"{strategy_final:,.0f} 円"
)

print(
    "Market Signal AI CAGR:",
    f"{strategy_cagr:.2f}%"
)

print("")
print(
    "売買回数:",
    len(trades)
)

print("")
print(
    "売買履歴:",
    "strategy_trades.csv"
)