import pandas as pd

# =========================================================
# Market Signal AI - Strategy Backtest v2
# Late Entry Filter v2
#
# 目的:
# 1) Buy & Hold
# 2) -15%以内のみSELL
# 3) 下落率制限なし
# 4) Late Entry Filter v2
#    -15%以内: 構造悪化型/急変型どちらでもSELL可
#    -15%超: 構造悪化型のみSELL可
#             急変型だけなら「遅すぎるSELL」として見送り
#
# Recoveryロジックは前回と同じにし、
# SELL側の改善効果だけを比較する。
# =========================================================

INPUT_FILE = "long_backtest_results.csv"

INITIAL_MONEY = 1_000_000
TRADE_DELAY = 1
MIN_RECOVERY_WAIT = 5

LATE_ENTRY_LIMIT = 15.0

# 警戒条件
STRUCTURAL_200MA_DIFF = -3.0
STRUCTURAL_BAA10Y = 2.5

SHOCK_SP500_20D = -7.0
SHOCK_VIX_20D = 60.0

CONFIRM_WINDOW = 5
CONFIRM_REQUIRED = 2


# =========================================================
# データ読み込み
# =========================================================

df = pd.read_csv(INPUT_FILE)
df["date"] = pd.to_datetime(df["date"])

required_columns = [
    "date",
    "sp500",
    "sp500_200ma_diff",
    "baa10y",
    "sp500_change_20d",
    "vix_change_20d",
    "vix_change_5d",
    "vix_change_10d",
    "baa_change_5d_pt",
    "baa_change_10d_pt",
    "sp500_change_5d",
    "sp500_change_10d",
]

missing = [c for c in required_columns if c not in df.columns]
if missing:
    raise ValueError(
        "long_backtest_results.csv に必要な列がありません: "
        + ", ".join(missing)
    )

df = df.sort_values("date").reset_index(drop=True)


# =========================================================
# Major Crash Risk
# =========================================================

# ① 構造悪化型
df["structural_raw"] = (
    (df["sp500_200ma_diff"] <= STRUCTURAL_200MA_DIFF)
    &
    (df["baa10y"] >= STRUCTURAL_BAA10Y)
)

# ② 急変型
df["shock_raw"] = (
    (df["sp500_change_20d"] <= SHOCK_SP500_20D)
    &
    (df["vix_change_20d"] >= SHOCK_VIX_20D)
)

# 直近5営業日のうち2日以上成立で確認済み
df["structural_confirm"] = (
    df["structural_raw"]
    .astype(int)
    .rolling(CONFIRM_WINDOW, min_periods=1)
    .sum()
    >= CONFIRM_REQUIRED
)

df["shock_confirm"] = (
    df["shock_raw"]
    .astype(int)
    .rolling(CONFIRM_WINDOW, min_periods=1)
    .sum()
    >= CONFIRM_REQUIRED
)

df["major_confirm"] = (
    df["structural_confirm"]
    |
    df["shock_confirm"]
)


# =========================================================
# 直近252営業日の高値からの下落率
# =========================================================

df["recent_peak"] = (
    df["sp500"]
    .rolling(252, min_periods=1)
    .max()
)

df["drawdown_from_peak"] = (
    (df["sp500"] / df["recent_peak"]) - 1
) * 100


# =========================================================
# Recovery Score
# =========================================================

df["recovery_score"] = (
    (df["vix_change_5d"] < 0).astype(int)
    + (df["vix_change_10d"] < 0).astype(int)
    + (df["baa_change_5d_pt"] < 0).astype(int)
    + (df["baa_change_10d_pt"] < 0).astype(int)
    + (df["sp500_change_5d"] > 0).astype(int)
    + (df["sp500_change_10d"] > 0).astype(int)
)

for score in [3, 4, 5, 6]:
    df[f"recovery_{score}_confirmed"] = (
        (df["recovery_score"] >= score)
        .astype(int)
        .rolling(3, min_periods=1)
        .sum()
        >= 2
    )


# =========================================================
# Buy & Hold
# =========================================================

start_price = float(df.iloc[0]["sp500"])
end_price = float(df.iloc[-1]["sp500"])

years = (
    (df.iloc[-1]["date"] - df.iloc[0]["date"]).days
    / 365.25
)

buy_hold_final = INITIAL_MONEY * end_price / start_price

buy_hold_cagr = (
    (buy_hold_final / INITIAL_MONEY) ** (1 / years) - 1
) * 100

buy_hold_equity = INITIAL_MONEY * df["sp500"] / start_price
buy_hold_peak = buy_hold_equity.cummax()
buy_hold_dd = buy_hold_equity / buy_hold_peak - 1
buy_hold_max_dd = buy_hold_dd.min() * 100


# =========================================================
# SELL eligibility
# =========================================================

def sell_allowed(row, mode):
    """
    return:
        allowed: bool
        reason: str
    """

    dd = float(row["drawdown_from_peak"])
    structural = bool(row["structural_confirm"])
    shock = bool(row["shock_confirm"])

    if not (structural or shock):
        return False, "NO_MAJOR_SIGNAL"

    if mode == "minus15":
        if dd >= -LATE_ENTRY_LIMIT:
            return True, "WITHIN_MINUS15"
        return False, "BLOCKED_BELOW_MINUS15"

    if mode == "none":
        return True, "NO_LATE_ENTRY_FILTER"

    if mode == "v2":
        # -15%以内なら、構造型・急変型どちらでもSELL可能
        if dd >= -LATE_ENTRY_LIMIT:
            if structural and shock:
                return True, "V2_WITHIN15_BOTH"
            elif structural:
                return True, "V2_WITHIN15_STRUCTURAL"
            else:
                return True, "V2_WITHIN15_SHOCK"

        # -15%を超えていても、構造悪化型ならSELL可能
        if structural:
            return True, "V2_DEEP_BUT_STRUCTURAL"

        # 急変型のみ & 既に-15%超 → 遅すぎるSELLとして見送り
        return False, "V2_BLOCKED_LATE_SHOCK_ONLY"

    raise ValueError(f"Unknown strategy mode: {mode}")


# =========================================================
# 1戦略をシミュレーション
# =========================================================

def run_strategy(name, mode):

    cash = 0.0
    shares = INITIAL_MONEY / start_price
    exposure = 1.0

    pending_order = None
    last_sell_index = -999

    trades = []
    blocked_signals = []
    equity_history = []
    exposure_history = []

    # 「eligibleがFalse→Trueになった時」だけSELL候補にする
    # これにより、2025のように最初はv2でブロックされても、
    # 後日構造悪化型へ変わった場合は改めて判定できる。
    prev_eligible = False

    for i, row in df.iterrows():

        price = float(row["sp500"])

        # -------------------------------------------------
        # 前営業日に出した注文を実行
        # -------------------------------------------------
        if (
            pending_order is not None
            and i >= pending_order["execute_index"]
        ):
            target = float(pending_order["target_exposure"])

            total_value = cash + shares * price
            target_stock_value = total_value * target
            current_stock_value = shares * price
            difference = target_stock_value - current_stock_value

            action = None

            if difference > 1e-9:
                shares += difference / price
                cash -= difference
                action = "BUY"

            elif difference < -1e-9:
                sell_value = -difference
                shares -= sell_value / price
                cash += sell_value
                action = "SELL"

            exposure = target

            if action is not None:
                trades.append({
                    "variant": name,
                    "date": row["date"].date().isoformat(),
                    "action": action,
                    "sp500": round(price, 4),
                    "target_exposure": round(exposure, 2),
                    "drawdown_from_peak": round(
                        float(row["drawdown_from_peak"]), 2
                    ),
                    "structural_confirm": bool(
                        row["structural_confirm"]
                    ),
                    "shock_confirm": bool(
                        row["shock_confirm"]
                    ),
                    "major_confirm": bool(
                        row["major_confirm"]
                    ),
                    "recovery_score": int(
                        row["recovery_score"]
                    ),
                    "trigger_date": pending_order["trigger_date"],
                    "trigger_reason": pending_order["reason"],
                })

            if target == 0.0:
                last_sell_index = i

            pending_order = None


        # -------------------------------------------------
        # 現在資産
        # -------------------------------------------------
        total_value = cash + shares * price

        equity_history.append(total_value)
        exposure_history.append(exposure)


        # -------------------------------------------------
        # SELL判定
        # -------------------------------------------------
        eligible, reason = sell_allowed(row, mode)

        # 「今までeligibleでなかった → 今日eligible」
        # の立ち上がりだけを新しいSELL候補にする
        eligible_start = eligible and not prev_eligible

        # major signal自体はあるがLate Entryで弾かれた瞬間を保存
        major_now = bool(row["major_confirm"])

        if (
            major_now
            and not eligible
            and exposure > 0
        ):
            # 同じブロック理由を毎日大量に記録しないため、
            # major_confirmの立ち上がり、または理由変化時のみ記録
            major_prev = (
                bool(df.iloc[i - 1]["major_confirm"])
                if i > 0 else False
            )

            if not major_prev:
                blocked_signals.append({
                    "variant": name,
                    "date": row["date"].date().isoformat(),
                    "sp500": round(price, 4),
                    "drawdown_from_peak": round(
                        float(row["drawdown_from_peak"]), 2
                    ),
                    "structural_confirm": bool(
                        row["structural_confirm"]
                    ),
                    "shock_confirm": bool(
                        row["shock_confirm"]
                    ),
                    "block_reason": reason,
                })

        if (
            eligible_start
            and exposure > 0.0
            and pending_order is None
        ):
            execute_index = i + TRADE_DELAY

            if execute_index < len(df):
                pending_order = {
                    "execute_index": execute_index,
                    "target_exposure": 0.0,
                    "trigger_date": row["date"].date().isoformat(),
                    "reason": reason,
                }

        prev_eligible = eligible


        # -------------------------------------------------
        # Recovery判定
        # -------------------------------------------------
        if (
            exposure < 1.0
            and not bool(row["major_confirm"])
            and (i - last_sell_index >= MIN_RECOVERY_WAIT)
            and pending_order is None
        ):
            target = exposure
            recovery_reason = None

            if bool(row["recovery_6_confirmed"]):
                target = max(target, 1.00)
                recovery_reason = "RECOVERY_100"

            elif bool(row["recovery_5_confirmed"]):
                target = max(target, 0.75)
                recovery_reason = "RECOVERY_75"

            elif bool(row["recovery_4_confirmed"]):
                target = max(target, 0.50)
                recovery_reason = "RECOVERY_50"

            elif bool(row["recovery_3_confirmed"]):
                target = max(target, 0.25)
                recovery_reason = "RECOVERY_25"

            if target > exposure:
                execute_index = i + TRADE_DELAY

                if execute_index < len(df):
                    pending_order = {
                        "execute_index": execute_index,
                        "target_exposure": target,
                        "trigger_date": row["date"].date().isoformat(),
                        "reason": recovery_reason,
                    }


    # =====================================================
    # 最終結果
    # =====================================================

    final_value = cash + shares * float(df.iloc[-1]["sp500"])

    cagr = (
        (final_value / INITIAL_MONEY) ** (1 / years) - 1
    ) * 100

    equity = pd.Series(equity_history, dtype=float)
    peak = equity.cummax()
    drawdown = equity / peak - 1
    max_dd = drawdown.min() * 100

    exposure_series = pd.Series(exposure_history, dtype=float)

    avg_market_exposure = exposure_series.mean() * 100
    days_below_100 = int((exposure_series < 0.999).sum())
    days_fully_out = int((exposure_series <= 0.001).sum())

    return {
        "name": name,
        "final_value": final_value,
        "cagr": cagr,
        "max_drawdown": max_dd,
        "trade_actions": len(trades),
        "days_below_100pct": days_below_100,
        "days_fully_out": days_fully_out,
        "avg_market_exposure_pct": avg_market_exposure,
        "trades": trades,
        "blocked_signals": blocked_signals,
    }


# =========================================================
# 戦略比較
# =========================================================

strategies = [
    run_strategy(
        "Sell_before_minus15",
        "minus15"
    ),
    run_strategy(
        "No_late_entry_filter",
        "none"
    ),
    run_strategy(
        "Late_Entry_Filter_v2",
        "v2"
    ),
]


# =========================================================
# 比較CSV
# =========================================================

comparison_rows = [{
    "strategy": "Buy_and_Hold",
    "final_value": round(buy_hold_final, 0),
    "cagr": round(buy_hold_cagr, 2),
    "max_drawdown": round(buy_hold_max_dd, 2),
    "trade_actions": 0,
    "days_below_100pct": 0,
    "days_fully_out": 0,
    "avg_market_exposure_pct": 100.0,
}]

for result in strategies:
    comparison_rows.append({
        "strategy": result["name"],
        "final_value": round(result["final_value"], 0),
        "cagr": round(result["cagr"], 2),
        "max_drawdown": round(result["max_drawdown"], 2),
        "trade_actions": result["trade_actions"],
        "days_below_100pct": result["days_below_100pct"],
        "days_fully_out": result["days_fully_out"],
        "avg_market_exposure_pct": round(
            result["avg_market_exposure_pct"], 2
        ),
    })

comparison_df = pd.DataFrame(comparison_rows)

comparison_df.to_csv(
    "strategy_comparison_v2.csv",
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# 全売買履歴
# =========================================================

all_trades = []

for result in strategies:
    all_trades.extend(result["trades"])

trades_df = pd.DataFrame(all_trades)

trades_df.to_csv(
    "strategy_trades_v2.csv",
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# Late Entryで見送ったシグナル
# =========================================================

all_blocked = []

for result in strategies:
    all_blocked.extend(result["blocked_signals"])

blocked_df = pd.DataFrame(all_blocked)

blocked_df.to_csv(
    "blocked_signals_v2.csv",
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# 重要局面だけ抜き出す
# =========================================================

if not trades_df.empty:
    trades_df["date_dt"] = pd.to_datetime(trades_df["date"])

    crisis_ranges = [
        ("Dotcom", "2000-01-01", "2003-12-31"),
        ("GFC", "2007-01-01", "2009-12-31"),
        ("COVID", "2020-01-01", "2020-12-31"),
        ("2022_Bear", "2022-01-01", "2022-12-31"),
        ("2025_Tariff", "2025-01-01", "2025-12-31"),
    ]

    crisis_trade_rows = []

    for crisis_name, start, end in crisis_ranges:
        mask = (
            (trades_df["date_dt"] >= pd.Timestamp(start))
            &
            (trades_df["date_dt"] <= pd.Timestamp(end))
        )

        temp = trades_df.loc[mask].copy()

        if not temp.empty:
            temp["crisis"] = crisis_name
            crisis_trade_rows.append(temp)

    if crisis_trade_rows:
        crisis_trades_df = pd.concat(
            crisis_trade_rows,
            ignore_index=True
        )
    else:
        crisis_trades_df = pd.DataFrame()

else:
    crisis_trades_df = pd.DataFrame()

crisis_trades_df.to_csv(
    "crisis_strategy_trades_v2.csv",
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# 結果表示
# =========================================================

print("")
print("==========================================")
print("Market Signal AI - Strategy Backtest v2")
print("==========================================")
print("")

print(comparison_df.to_string(index=False))

print("")
print("出力ファイル:")
print("  strategy_comparison_v2.csv")
print("  strategy_trades_v2.csv")
print("  blocked_signals_v2.csv")
print("  crisis_strategy_trades_v2.csv")
print("")

print("Late Entry Filter v2:")
print("  -15%以内 -> 構造型/急変型どちらでもSELL可")
print("  -15%超   -> 構造悪化型のみSELL可")
print("             急変型だけならSELL見送り")
