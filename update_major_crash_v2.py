import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd


# ============================================================
# Market Signal AI - Major Crash Risk V2 (production updater)
#
# Uses FRED daily series:
#   SP500   : S&P 500
#   VIXCLS  : CBOE VIX
#   BAA10Y  : Moody's Baa yield relative to 10Y Treasury
#
# Rules (current experimental V2):
#
# Structural deterioration:
#   S&P500 <= 200DMA - 3%
#   AND BAA10Y >= 2.5
#
# Shock deterioration:
#   S&P500 20-business-day change <= -7%
#   AND VIX 20-business-day change >= +60%
#
# Confirmation:
#   Condition true on >=2 of last 5 S&P trading dates
#
# Late Entry Filter V2:
#   Major risk not confirmed -> HOLD
#   Confirmed & drawdown >= -15% -> EVACUATION_CONSIDER
#   Confirmed & drawdown < -15% & structural confirmed
#       -> EVACUATION_CONSIDER_STRUCTURAL
#   Confirmed & drawdown < -15% & shock only
#       -> LATE_ENTRY_CAUTION
#
# This script MERGES majorCrashV2 into the existing market.json,
# so the existing app data is preserved.
# ============================================================


FRED_API_KEY = os.environ.get("FRED_API_KEY", "").strip()
MARKET_JSON = Path("market.json")

LOOKBACK_CALENDAR_DAYS = 900

STRUCTURAL_200MA_DIFF = -3.0
STRUCTURAL_BAA10Y = 2.5

SHOCK_SP500_20D = -7.0
SHOCK_VIX_20D = 60.0

CONFIRM_WINDOW = 5
CONFIRM_REQUIRED = 2

LATE_ENTRY_LIMIT = -15.0


def die(message: str):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def fred_series(series_id: str, observation_start: str) -> pd.Series:
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": observation_start,
        "sort_order": "asc",
        "limit": 100000,
    }

    url = (
        "https://api.stlouisfed.org/fred/series/observations?"
        + urlencode(params)
    )

    with urlopen(url, timeout=30) as response:
        payload = json.load(response)

    observations = payload.get("observations", [])

    rows = []

    for obs in observations:
        value = obs.get("value")

        if value in (None, ".", ""):
            continue

        try:
            numeric = float(value)
        except ValueError:
            continue

        rows.append(
            (
                pd.Timestamp(obs["date"]),
                numeric,
            )
        )

    if not rows:
        raise RuntimeError(
            f"No usable observations returned for {series_id}"
        )

    s = pd.Series(
        data=[v for _, v in rows],
        index=[d for d, _ in rows],
        name=series_id,
        dtype=float,
    )

    return s[~s.index.duplicated(keep="last")].sort_index()


def pct_change_from_periods(series: pd.Series, periods: int):
    return (series / series.shift(periods) - 1.0) * 100.0


def round_or_none(value, digits=2):
    if pd.isna(value):
        return None
    return round(float(value), digits)


def load_existing_market_json():
    if not MARKET_JSON.exists():
        return {}

    try:
        with MARKET_JSON.open("r", encoding="utf-8") as f:
            existing = json.load(f)

        if not isinstance(existing, dict):
            print(
                "WARNING: market.json root was not an object. "
                "Starting with a new object."
            )
            return {}

        return existing

    except Exception as e:
        die(f"Could not read market.json: {e}")


def main():
    if not FRED_API_KEY:
        die(
            "FRED_API_KEY is missing. "
            "Add it to GitHub Actions Secrets."
        )

    start = (
        date.today() - timedelta(days=LOOKBACK_CALENDAR_DAYS)
    ).isoformat()

    print(f"Fetching FRED data from {start} ...")

    sp500 = fred_series("SP500", start)
    vix = fred_series("VIXCLS", start)
    baa = fred_series("BAA10Y", start)

    # S&P500 dates are the trading-date spine.
    df = pd.DataFrame(index=sp500.index)
    df["sp500"] = sp500

    # FRED series may have slightly different holiday / publication dates.
    # Forward-fill onto S&P500 trading dates.
    df["vix"] = vix.reindex(df.index).ffill()
    df["baa10y"] = baa.reindex(df.index).ffill()

    df = df.dropna(
        subset=["sp500", "vix", "baa10y"]
    ).copy()

    if len(df) < 260:
        die(
            f"Not enough aligned observations ({len(df)}). "
            "Need at least 260."
        )

    # --------------------------------------------------------
    # Features
    # --------------------------------------------------------

    df["sp500_200ma"] = (
        df["sp500"].rolling(200).mean()
    )

    df["sp500_200ma_diff"] = (
        (df["sp500"] / df["sp500_200ma"]) - 1.0
    ) * 100.0

    df["recent_252d_peak"] = (
        df["sp500"].rolling(252, min_periods=1).max()
    )

    df["drawdown_from_peak"] = (
        (df["sp500"] / df["recent_252d_peak"]) - 1.0
    ) * 100.0

    df["sp500_change_20d"] = pct_change_from_periods(
        df["sp500"], 20
    )

    df["vix_change_20d"] = pct_change_from_periods(
        df["vix"], 20
    )

    # --------------------------------------------------------
    # Raw signal
    # --------------------------------------------------------

    df["structural_raw"] = (
        (df["sp500_200ma_diff"] <= STRUCTURAL_200MA_DIFF)
        &
        (df["baa10y"] >= STRUCTURAL_BAA10Y)
    )

    df["shock_raw"] = (
        (df["sp500_change_20d"] <= SHOCK_SP500_20D)
        &
        (df["vix_change_20d"] >= SHOCK_VIX_20D)
    )

    # --------------------------------------------------------
    # 2-of-5 confirmation
    # --------------------------------------------------------

    df["structural_count_5d"] = (
        df["structural_raw"]
        .astype(int)
        .rolling(CONFIRM_WINDOW, min_periods=1)
        .sum()
    )

    df["shock_count_5d"] = (
        df["shock_raw"]
        .astype(int)
        .rolling(CONFIRM_WINDOW, min_periods=1)
        .sum()
    )

    df["structural_confirm"] = (
        df["structural_count_5d"] >= CONFIRM_REQUIRED
    )

    df["shock_confirm"] = (
        df["shock_count_5d"] >= CONFIRM_REQUIRED
    )

    df["major_confirm"] = (
        df["structural_confirm"]
        |
        df["shock_confirm"]
    )

    latest = df.iloc[-1]
    latest_date = df.index[-1].date()

    structural = bool(latest["structural_confirm"])
    shock = bool(latest["shock_confirm"])
    confirmed = bool(latest["major_confirm"])

    dd = float(latest["drawdown_from_peak"])

    # --------------------------------------------------------
    # Late Entry Filter V2 action
    # --------------------------------------------------------

    reasons = []

    if structural:
        reasons.append(
            "構造悪化型：S&P500の200日線乖離とBAA信用スプレッドが警戒条件"
        )

    if shock:
        reasons.append(
            "急変型：S&P500の20日下落率とVIXの20日上昇率が警戒条件"
        )

    if not confirmed:
        action = "HOLD"
        action_ja = "🟢 HOLD"
        level = "LOW"
        message = (
            "Major Crash Risk V2は確認されていません。"
            "通常の長期保有を基本とする状態です。"
        )

    elif dd >= LATE_ENTRY_LIMIT:
        action = "EVACUATION_CONSIDER"
        action_ja = "🟠 退避検討"
        level = "HIGH"
        message = (
            "Major Crash Risk V2が確認されています。"
            "直近高値からの下落が15%以内なので、"
            "退避を検討できる領域です。"
        )

    elif structural:
        action = "EVACUATION_CONSIDER_STRUCTURAL"
        action_ja = "🔴 構造悪化・退避検討"
        level = "VERY_HIGH"
        message = (
            "すでに15%を超えて下落していますが、"
            "構造悪化型が確認されています。"
            "長期的な悪化が続く可能性を警戒する状態です。"
        )

    else:
        action = "LATE_ENTRY_CAUTION"
        action_ja = "⚠️ 高リスク・新規全面退避は慎重"
        level = "HIGH_LATE"
        message = (
            "Major Crash Riskは高いものの、"
            "すでに15%を超えて下落し、確認されているのは"
            "急変型です。今からの全面退避は遅い可能性があります。"
        )

    if not reasons:
        reasons.append(
            "構造悪化型・急変型とも2/5日確認条件を満たしていません"
        )

    stale_days = (date.today() - latest_date).days

    result = {
        "version": "2.0-experimental",
        "asOf": latest_date.isoformat(),
        "dataStaleDays": stale_days,

        "confirmed": confirmed,

        "structural": {
            "rawToday": bool(latest["structural_raw"]),
            "confirmed": structural,
            "countLast5": int(latest["structural_count_5d"]),
            "requiredCount": CONFIRM_REQUIRED,
        },

        "shock": {
            "rawToday": bool(latest["shock_raw"]),
            "confirmed": shock,
            "countLast5": int(latest["shock_count_5d"]),
            "requiredCount": CONFIRM_REQUIRED,
        },

        "metrics": {
            "sp500": round_or_none(latest["sp500"]),
            "sp500_200ma": round_or_none(
                latest["sp500_200ma"]
            ),
            "sp500_200maDiffPct": round_or_none(
                latest["sp500_200ma_diff"]
            ),
            "baa10y": round_or_none(
                latest["baa10y"]
            ),
            "sp500Change20dPct": round_or_none(
                latest["sp500_change_20d"]
            ),
            "vix": round_or_none(latest["vix"]),
            "vixChange20dPct": round_or_none(
                latest["vix_change_20d"]
            ),
            "recent252dPeak": round_or_none(
                latest["recent_252d_peak"]
            ),
            "drawdownFromPeakPct": round_or_none(dd),
        },

        "action": action,
        "actionJa": action_ja,
        "level": level,
        "message": message,
        "reasons": reasons,

        "rules": {
            "structural": {
                "sp500_200maDiffPctLte": STRUCTURAL_200MA_DIFF,
                "baa10yGte": STRUCTURAL_BAA10Y,
            },
            "shock": {
                "sp500Change20dPctLte": SHOCK_SP500_20D,
                "vixChange20dPctGte": SHOCK_VIX_20D,
            },
            "confirmation": {
                "windowTradingDays": CONFIRM_WINDOW,
                "requiredDays": CONFIRM_REQUIRED,
            },
            "lateEntryLimitPct": LATE_ENTRY_LIMIT,
        },

        "note": (
            "Experimental risk indicator for informational use. "
            "It is not a validated prediction model or investment advice."
        ),
    }

    market = load_existing_market_json()
    market["majorCrashV2"] = result

    with MARKET_JSON.open("w", encoding="utf-8") as f:
        json.dump(
            market,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("")
    print("========================================")
    print("Major Crash Risk V2")
    print("========================================")
    print(f"As of:                 {latest_date}")
    print(f"Action:                {action_ja}")
    print(f"Confirmed:             {confirmed}")
    print(f"Structural confirmed:  {structural}")
    print(f"Shock confirmed:       {shock}")
    print(
        f"Drawdown from 252d peak: {dd:.2f}%"
    )
    print(
        f"S&P500 vs 200DMA:        "
        f"{latest['sp500_200ma_diff']:.2f}%"
    )
    print(f"BAA10Y:                  {latest['baa10y']:.2f}")
    print(
        f"S&P500 20d:              "
        f"{latest['sp500_change_20d']:.2f}%"
    )
    print(
        f"VIX 20d:                 "
        f"{latest['vix_change_20d']:.2f}%"
    )
    print("")
    print("market.json updated successfully.")


if __name__ == "__main__":
    main()
