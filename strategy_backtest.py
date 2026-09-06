import pandas as pd


INPUT_FILE = "long_backtest_results.csv"

INITIAL_MONEY = 1_000_000

TRADE_DELAY = 1

# SELL後、最低5営業日はRecoveryを待つ
MIN_RECOVERY_WAIT = 5


# ==========================================
# データ読み込み
# ==========================================

df = pd.read_csv(INPUT_FILE)

df["date"] = pd.to_datetime(df["date"])


# ==========================================
# Major Crash Risk
# ==========================================

# ① 構造悪化型
structural_risk = (
    (df["sp500_200ma_diff"] <= -3)
    &
    (df["baa10y"] >= 2.5)
)

# ② 急変型
shock_risk = (
    (df["sp500_change_20d"] <= -7)
    &
    (df["vix_change_20d"] >= 60)
)

df["major_raw"] = (
    structural_risk
    |
    shock_risk
)


# ==========================================
# 直近5日のうち2日以上で確認
# ==========================================

df["major_confirm"] = (
    df["major_raw"]
    .rolling(
        5,
        min_periods=1
    )
    .sum()
    >= 2
)


# ==========================================
# 新しい警戒エピソード開始日
# ==========================================

df["major_episode_start"] = (
    df["major_confirm"]
    &
    ~df["major_confirm"]
    .shift(
        1,
        fill_value=False
    )
)


# ==========================================
# 直近252営業日の高値からの下落率
# ==========================================

df["recent_peak"] = (
    df["sp500"]
    .rolling(
        252,
        min_periods=1
    )
    .max()
)

df["drawdown_from_peak"] = (
    (
        df["sp500"]
        /
        df["recent_peak"]
    )
    - 1
) * 100


# ==========================================
# Recovery Score
# ==========================================

df["recovery_score"] = (

    # VIX低下
    (df["vix_change_5d"] < 0).astype(int)

    +

    (df["vix_change_10d"] < 0).astype(int)

    +

    # 信用市場改善
    (df["baa_change_5d_pt"] < 0).astype(int)

    +

    (df["baa_change_10d_pt"] < 0).astype(int)

    +

    # 株価反発
    (df["sp500_change_5d"] > 0).astype(int)

    +

    (df["sp500_change_10d"] > 0).astype(int)
)


# ==========================================
# Recoveryも2/3日確認
# ==========================================

for score in [3, 4, 5, 6]:

    df[f"recovery_{score}_confirmed"] = (

        (
            df["recovery_score"]
            >= score
        )
        .rolling(
            3,
            min_periods=1
        )
        .sum()
        >= 2
    )


# ==========================================
# Buy & Hold
# ==========================================

start_price = df.iloc[0]["sp500"]
end_price = df.iloc[-1]["sp500"]

buy_hold_final = (
    INITIAL_MONEY
    *
    end_price
    /
    start_price
)

years = (
    (
        df.iloc[-1]["date"]
        -
        df.iloc[0]["date"]
    ).days
    /
    365.25
)

buy_hold_cagr = (
    (
        buy_hold_final
        /
        INITIAL_MONEY
    )
    ** (1 / years)
    - 1
) * 100


buy_hold_equity = (
    INITIAL_MONEY
    *
    df["sp500"]
    /
    start_price
)

buy_hold_peak = (
    buy_hold_equity.cummax()
)

buy_hold_dd = (
    buy_hold_equity
    /
    buy_hold_peak
    - 1
)

buy_hold_max_dd = (
    buy_hold_dd.min()
    * 100
)


# ==========================================
# 1戦略をシミュレーション
# ==========================================

def run_strategy(
    name,
    max_entry_drawdown=None
):

    cash = 0.0

    shares = (
        INITIAL_MONEY
        /
        start_price
    )

    exposure = 1.0

    pending_target = None

    last_sell_index = -999

    trades = []

    equity_history = []

    partial_days = 0


    for i, row in df.iterrows():

        price = row["sp500"]


        # ==================================
        # 前日の注文を実行
        # ==================================

        if (
            pending_target is not None
            and
            i >= pending_target["index"]
        ):

            target = (
                pending_target["exposure"]
            )

            total_value = (
                cash
                +
                shares * price
            )

            target_stock_value = (
                total_value
                *
                target
            )

            current_stock_value = (
                shares
                *
                price
            )

            difference = (
                target_stock_value
                -
                current_stock_value
            )


            # 買い
            if difference > 0:

                shares += (
                    difference
                    /
                    price
                )

                cash -= difference

                action = "BUY"


            # 売り
            elif difference < 0:

                sell_value = (
                    -difference
                )

                shares -= (
                    sell_value
                    /
                    price
                )

                cash += sell_value

                action = "SELL"


            else:

                action = None


            exposure = target


            if action:

                trades.append({
                    "variant": name,
                    "date": row["date"],
                    "action": action,
                    "sp500": price,
                    "exposure": exposure,
                    "drawdown_from_peak":
                        row[
                            "drawdown_from_peak"
                        ],
                    "recovery_score":
                        row[
                            "recovery_score"
                        ]
                })


            if target == 0:

                last_sell_index = i


            pending_target = None


        # ==================================
        # 現在の資産
        # ==================================

        total_value = (
            cash
            +
            shares * price
        )

        equity_history.append(
            total_value
        )


        if exposure < 0.999:

            partial_days += 1


        # ==================================
        # Major Crash Risk
        # ==================================

        if row["major_episode_start"]:

            current_dd = (
                row[
                    "drawdown_from_peak"
                ]
            )


            # 下落しすぎフィルター
            if max_entry_drawdown is None:

                allowed = True

            else:

                allowed = (
                    current_dd
                    >=
                    -max_entry_drawdown
                )


            if (
                allowed
                and
                exposure > 0
            ):

                pending_target = {
                    "index":
                        i + TRADE_DELAY,

                    "exposure":
                        0.0
                }

                continue


        # ==================================
        # Recovery
        # ==================================

        if (
            exposure < 1.0
            and
            not row["major_confirm"]
            and
            (
                i
                -
                last_sell_index
                >=
                MIN_RECOVERY_WAIT
            )
            and
            pending_target is None
        ):

            target = exposure


            # 100%
            if row[
                "recovery_6_confirmed"
            ]:

                target = max(
                    target,
                    1.00
                )


            # 75%
            elif row[
                "recovery_5_confirmed"
            ]:

                target = max(
                    target,
                    0.75
                )


            # 50%
            elif row[
                "recovery_4_confirmed"
            ]:

                target = max(
                    target,
                    0.50
                )


            # 25%
            elif row[
                "recovery_3_confirmed"
            ]:

                target = max(
                    target,
                    0.25
                )


            if target > exposure:

                pending_target = {
                    "index":
                        i + TRADE_DELAY,

                    "exposure":
                        target
                }


    # ======================================
    # 最終結果
    # ======================================

    final_value = (
        cash
        +
        shares
        *
        df.iloc[-1]["sp500"]
    )


    cagr = (
        (
            final_value
            /
            INITIAL_MONEY
        )
        ** (1 / years)
        - 1
    ) * 100


    equity = pd.Series(
        equity_history
    )

    peak = equity.cummax()

    drawdown = (
        equity
        /
        peak
        - 1
    )

    max_dd = (
        drawdown.min()
        * 100
    )


    return {

        "name": name,

        "final_value":
            final_value,

        "cagr":
            cagr,

        "max_drawdown":
            max_dd,

        "trade_actions":
            len(trades),

        "days_below_100pct":
            partial_days,

        "market_exposure_pct":
            (
                1
                -
                partial_days
                /
                len(df)
            )
            * 100,

        "trades":
            trades
    }


# ==========================================
# 4パターン比較
# ==========================================

strategies = [

    run_strategy(
        "Sell_before_minus10",
        10
    ),

    run_strategy(
        "Sell_before_minus12_5",
        12.5
    ),

    run_strategy(
        "Sell_before_minus15",
        15
    ),

    run_strategy(
        "No_late_entry_filter",
        None
    )
]


# ==========================================
# 比較CSV
# ==========================================

comparison_rows = []

comparison_rows.append({

    "strategy":
        "Buy_and_Hold",

    "final_value":
        round(
            buy_hold_final,
            0
        ),

    "cagr":
        round(
            buy_hold_cagr,
            2
        ),

    "max_drawdown":
        round(
            buy_hold_max_dd,
            2
        ),

    "trade_actions":
        0,

    "days_below_100pct":
        0,

    "market_exposure_pct":
        100.0
})


for result in strategies:

    comparison_rows.append({

        "strategy":
            result["name"],

        "final_value":
            round(
                result["final_value"],
                0
            ),

        "cagr":
            round(
                result["cagr"],
                2
            ),

        "max_drawdown":
            round(
                result["max_drawdown"],
                2
            ),

        "trade_actions":
            result["trade_actions"],

        "days_below_100pct":
            result[
                "days_below_100pct"
            ],

        "market_exposure_pct":
            round(
                result[
                    "market_exposure_pct"
                ],
                2
            )
    })


comparison_df = pd.DataFrame(
    comparison_rows
)

comparison_df.to_csv(
    "strategy_comparison.csv",
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# 全売買履歴
# ==========================================

all_trades = []

for result in strategies:

    all_trades.extend(
        result["trades"]
    )


pd.DataFrame(
    all_trades
).to_csv(
    "strategy_trades.csv",
    index=False,
    encoding="utf-8-sig"
)


# ==========================================
# 結果表示
# ==========================================

print("")
print("==============================")
print("Major Crash Strategy Test")
print("==============================")
print("")

print(
    comparison_df.to_string(
        index=False
    )
)

print("")
print(
    "出力: strategy_comparison.csv"
)

print(
    "出力: strategy_trades.csv"
)