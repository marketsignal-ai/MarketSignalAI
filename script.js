// ==========================
// Market Signal AI
// Version 2.0
// Major Crash Risk V2 integrated
// ==========================

fetch("market.json?t=" + Date.now())
  .then(response => {
    if (!response.ok) {
      throw new Error("market.json HTTP error: " + response.status);
    }
    return response.json();
  })
  .then(data => {

    // ==========================
    // 基本市場データ
    // ==========================

    document.getElementById("sp500").textContent =
      "S&P500： " + data.sp500;

    document.getElementById("nasdaq100").textContent =
      "NASDAQ100： " + data.nasdaq100;

    document.getElementById("vix").textContent =
      "VIX： " + data.vix;

    document.getElementById("usdjpy").textContent =
      "ドル円： " + data.usdjpy;

    document.getElementById("sp500_200ma").textContent =
      "S&P500 200日移動平均： " + data.sp500_200ma;

    document.getElementById("sp500_200ma_diff").textContent =
      "200日線乖離率： " + data.sp500_200ma_diff + "%";

    document.getElementById("yield_curve").textContent =
      "長短金利差（10年-2年）： " + data.yield_curve + "%";

    document.getElementById("high_yield_spread").textContent =
      "ハイイールド債スプレッド： " +
      data.high_yield_spread + "%";

    document.getElementById("initial_claims").textContent =
      "新規失業保険申請件数： " +
      Number(data.initial_claims).toLocaleString() + "件";


    // ==========================
    // 指標の色
    // ==========================

    const vixElement =
      document.getElementById("vix");

    const diffElement =
      document.getElementById("sp500_200ma_diff");

    if (data.vix < 20) {
      vixElement.style.color = "green";
    } else if (data.vix < 30) {
      vixElement.style.color = "orange";
    } else {
      vixElement.style.color = "red";
    }

    if (data.sp500_200ma_diff >= 0) {
      diffElement.style.color = "green";
    } else {
      diffElement.style.color = "red";
    }


    // ==========================
    // Base Risk Score
    // ==========================

    let baseScore = 0;
    let reasons = [];

    // VIX
    if (data.vix >= 30) {
      baseScore += 3;
      reasons.push("VIXが30以上");
    } else if (data.vix >= 25) {
      baseScore += 2;
      reasons.push("VIXが25以上");
    } else if (data.vix >= 20) {
      baseScore += 1;
      reasons.push("VIXが20以上");
    }

    // S&P500 と 200日移動平均
    if (data.sp500_200ma_diff <= -10) {
      baseScore += 3;
      reasons.push(
        "S&P500が200日線を10%以上下回る"
      );
    } else if (data.sp500_200ma_diff <= -5) {
      baseScore += 2;
      reasons.push(
        "S&P500が200日線を5%以上下回る"
      );
    } else if (data.sp500_200ma_diff < 0) {
      baseScore += 1;
      reasons.push(
        "S&P500が200日線を下回る"
      );
    }

    // HYスプレッド
    if (data.high_yield_spread >= 6) {
      baseScore += 3;
      reasons.push(
        "信用市場のストレスが非常に高い"
      );
    } else if (data.high_yield_spread >= 5) {
      baseScore += 2;
      reasons.push(
        "信用市場のストレスが高い"
      );
    } else if (data.high_yield_spread >= 4) {
      baseScore += 1;
      reasons.push(
        "信用市場に警戒感"
      );
    }


    // ==========================
    // Sudden Risk Score
    // ==========================

    const suddenScore =
      Number(data.sudden_score || 0);


    // ==========================
    // Final Risk
    // ==========================

    let weather;
    let risk;
    let comment;
    let action1;
    let action2;

    if (
      baseScore >= 7 ||
      suddenScore >= 5
    ) {

      weather = "⛈️ 危険";
      risk = "非常に高い";

      comment =
        "市場ストレスまたは急変シグナルが強く出ています。";

      action1 =
        "新規投資は慎重に";

      action2 =
        "市場状況を毎日確認";

    } else if (
      baseScore >= 5 ||
      suddenScore >= 3
    ) {

      weather = "🌧️ 警戒";
      risk = "高い";

      comment =
        "市場に警戒シグナルが出ています。";

      action1 =
        "積立は継続";

      action2 =
        "追加投資は慎重に";

    } else if (
      baseScore >= 3 ||
      suddenScore >= 2
    ) {

      weather = "☁️ 注意";
      risk = "中程度";

      comment =
        "一部の指標に注意が必要です。";

      action1 =
        "積立継続";

      action2 =
        "市場の変化を確認";

    } else {

      weather = "☀️ 晴れ";
      risk = "低い";

      comment =
        "主要な市場ストレス指標は現在落ち着いています。";

      action1 =
        "積立継続";

      action2 =
        "売却不要";
    }


    // ==========================
    // Base / Sudden 画面表示
    // ==========================

    document.getElementById(
      "weather"
    ).textContent = weather;

    document.getElementById(
      "risk"
    ).textContent =
      "市場リスク：" + risk;

    document.getElementById(
      "riskScore"
    ).textContent =
      "Base Risk Score： " +
      baseScore +
      " / 9";

    document.getElementById(
      "suddenScore"
    ).textContent =
      "急変スコア： " +
      suddenScore +
      " / 6";

    document.getElementById(
      "sp500Change"
    ).textContent =
      "S&P500 前日比： " +
      data.sp500_daily_change +
      "%";

    document.getElementById(
      "vixChange"
    ).textContent =
      "VIX 前日比： " +
      data.vix_daily_change +
      "%";

    document.getElementById(
      "hyChange"
    ).textContent =
      "HYスプレッド前日差： " +
      data.high_yield_daily_change +
      "pt";


    // ==========================
    // 急変指標の色
    // ==========================

    const sp500ChangeElement =
      document.getElementById(
        "sp500Change"
      );

    const vixChangeElement =
      document.getElementById(
        "vixChange"
      );

    const hyChangeElement =
      document.getElementById(
        "hyChange"
      );

    sp500ChangeElement.style.color =
      data.sp500_daily_change >= 0
        ? "green"
        : "red";

    vixChangeElement.style.color =
      data.vix_daily_change <= 0
        ? "green"
        : "red";

    hyChangeElement.style.color =
      data.high_yield_daily_change <= 0
        ? "green"
        : "red";


    // ==========================
    // Sudden Risk 判定理由
    // ==========================

    const suddenElement =
      document.getElementById(
        "suddenScore"
      );

    let suddenReasons = [];

    // S&P500
    if (
      data.sp500_daily_change <= -3
    ) {

      suddenReasons.push(
        "・S&P500が3%以上下落 → 2点"
      );

    } else if (
      data.sp500_daily_change <= -2
    ) {

      suddenReasons.push(
        "・S&P500が2%以上下落 → 1点"
      );

    } else {

      suddenReasons.push(
        "・S&P500の急落なし → 0点"
      );
    }

    // VIX
    if (
      data.vix_daily_change >= 30
    ) {

      suddenReasons.push(
        "・VIXが30%以上上昇 → 2点"
      );

    } else if (
      data.vix_daily_change >= 15
    ) {

      suddenReasons.push(
        "・VIXが15%以上上昇 → 1点"
      );

    } else {

      suddenReasons.push(
        "・VIXの急上昇なし → 0点"
      );
    }

    // HY
    if (
      data.high_yield_daily_change >= 0.50
    ) {

      suddenReasons.push(
        "・HYスプレッドが0.50pt以上拡大 → 2点"
      );

    } else if (
      data.high_yield_daily_change >= 0.25
    ) {

      suddenReasons.push(
        "・HYスプレッドが0.25pt以上拡大 → 1点"
      );

    } else {

      suddenReasons.push(
        "・信用スプレッドの急拡大なし → 0点"
      );
    }

    document.getElementById(
      "suddenReasons"
    ).textContent =
      suddenReasons.join("\n");

    if (suddenScore <= 1) {

      suddenElement.style.color =
        "green";

    } else if (
      suddenScore <= 3
    ) {

      suddenElement.style.color =
        "orange";

    } else {

      suddenElement.style.color =
        "red";
    }


    // ==========================
    // 行動・AIコメント
    // ==========================

    document.getElementById(
      "action1"
    ).textContent = action1;

    document.getElementById(
      "action2"
    ).textContent = action2;

    document.getElementById(
      "aiComment"
    ).textContent = comment;


    // ==========================
    // Base Risk 判定理由
    // ==========================

    let reasonText = "";

    if (reasons.length === 0) {

      reasonText =
        "・VIXは安定しています\n" +
        "・S&P500は200日移動平均線より上です\n" +
        "・ハイイールド債スプレッドは低水準です";

    } else {

      reasonText =
        reasons
          .map(
            reason =>
              "・" + reason
          )
          .join("\n");
    }

    document.getElementById(
      "riskReasons"
    ).textContent =
      reasonText;


    // ==========================
    // 市場状況
    // ==========================

    let trendStatus;

    if (
      data.sp500_200ma_diff >= 0
    ) {

      trendStatus =
        "🟢 市場トレンド";

    } else if (
      data.sp500_200ma_diff >= -5
    ) {

      trendStatus =
        "🟡 市場トレンド";

    } else {

      trendStatus =
        "🔴 市場トレンド";
    }


    let sentimentStatus;

    if (data.vix < 20) {

      sentimentStatus =
        "🟢 市場心理";

    } else if (
      data.vix < 30
    ) {

      sentimentStatus =
        "🟡 市場心理";

    } else {

      sentimentStatus =
        "🔴 市場心理";
    }


    let economyStatus;

    if (
      data.yield_curve >= 0 &&
      data.initial_claims < 300000
    ) {

      economyStatus =
        "🟢 景気";

    } else if (
      data.yield_curve >= -0.5 &&
      data.initial_claims < 350000
    ) {

      economyStatus =
        "🟡 景気";

    } else {

      economyStatus =
        "🔴 景気";
    }


    let fxStatus;

    if (
      data.usdjpy < 150
    ) {

      fxStatus =
        "🟢 為替";

    } else if (
      data.usdjpy < 160
    ) {

      fxStatus =
        "🟡 為替";

    } else {

      fxStatus =
        "🔴 為替";
    }


    document.getElementById(
      "trendStatus"
    ).textContent =
      trendStatus;

    document.getElementById(
      "sentimentStatus"
    ).textContent =
      sentimentStatus;

    document.getElementById(
      "economyStatus"
    ).textContent =
      economyStatus;

    document.getElementById(
      "fxStatus"
    ).textContent =
      fxStatus;


    // ==========================================
    // 🚨 Major Crash Risk V2
    // ==========================================

    const major =
      data.majorCrashV2;


    // V2データがまだ無い場合
    if (!major) {

      document.getElementById(
        "majorAction"
      ).textContent =
        "⚪ V2データなし";

      document.getElementById(
        "majorMessage"
      ).textContent =
        "market.json にMajor Crash Risk V2のデータがありません。";

      document.getElementById(
        "majorStructural"
      ).textContent =
        "---";

      document.getElementById(
        "majorShock"
      ).textContent =
        "---";

      document.getElementById(
        "majorDrawdown"
      ).textContent =
        "---";

      document.getElementById(
        "majorConfirmed"
      ).textContent =
        "---";

      return;
    }


    // ==========================
    // V2基本表示
    // ==========================

    const majorCard =
      document.querySelector(
        ".major-risk-card"
      );

    document.getElementById(
      "majorAction"
    ).textContent =
      major.actionJa ||
      major.action ||
      "---";

    document.getElementById(
      "majorMessage"
    ).textContent =
      major.message || "";


    // ==========================
    // Structural / Shock
    // ==========================

    const structural =
      Boolean(
        major.structural &&
        major.structural.confirmed
      );

    const shock =
      Boolean(
        major.shock &&
        major.shock.confirmed
      );

    const structuralCount =
      major.structural?.countLast5 ?? 0;

    const shockCount =
      major.shock?.countLast5 ?? 0;


    document.getElementById(
      "majorStructural"
    ).textContent =
      structural
        ? "⚠️ 確認済み " +
          structuralCount +
          "/5"
        : "○ 未確認 " +
          structuralCount +
          "/5";


    document.getElementById(
      "majorShock"
    ).textContent =
      shock
        ? "⚠️ 確認済み " +
          shockCount +
          "/5"
        : "○ 未確認 " +
          shockCount +
          "/5";


    // ==========================
    // V2 Metrics
    // ==========================

    const metrics =
      major.metrics || {};


    const formatPct =
      value => {

        if (
          value === null ||
          value === undefined
        ) {
          return "---";
        }

        return (
          Number(value).toFixed(2) +
          "%"
        );
      };


    const formatNum =
      value => {

        if (
          value === null ||
          value === undefined
        ) {
          return "---";
        }

        return Number(
          value
        ).toFixed(2);
      };


    document.getElementById(
      "majorDrawdown"
    ).textContent =
      formatPct(
        metrics.drawdownFromPeakPct
      );


    document.getElementById(
      "majorConfirmed"
    ).textContent =
      major.confirmed
        ? "⚠️ Major Risk"
        : "🟢 未確認";


    // ==========================
    // V2詳細
    // ==========================

    document.getElementById(
      "major200maDiff"
    ).textContent =
      "S&P500 vs 200DMA： " +
      formatPct(
        metrics.sp500_200maDiffPct
      );


    document.getElementById(
      "majorBaa10y"
    ).textContent =
      "BAA10Y： " +
      formatNum(
        metrics.baa10y
      );


    document.getElementById(
      "majorSp500Change20d"
    ).textContent =
      "S&P500 20日変化率： " +
      formatPct(
        metrics.sp500Change20dPct
      );


    document.getElementById(
      "majorVixChange20d"
    ).textContent =
      "VIX 20日変化率： " +
      formatPct(
        metrics.vixChange20dPct
      );


    document.getElementById(
      "majorAsOf"
    ).textContent =
      "データ基準日： " +
      (
        major.asOf ||
        "---"
      );


    // ==========================
    // V2判定理由
    // ==========================

    const majorReasons =
      Array.isArray(
        major.reasons
      )
        ? major.reasons
        : [];


    document.getElementById(
      "majorReasons"
    ).textContent =
      majorReasons.length > 0
        ? majorReasons
            .map(
              reason =>
                "・" + reason
            )
            .join("\n")
        : "・判定理由なし";


    // ==========================
    // V2カード色
    // ==========================

    majorCard.classList.remove(
      "major-low",
      "major-warning",
      "major-danger",
      "major-late"
    );


    switch (major.action) {

      // -15%以内でMajor Risk
      case "EVACUATION_CONSIDER":

        majorCard.classList.add(
          "major-warning"
        );

        break;


      // -15%超でも構造悪化
      case "EVACUATION_CONSIDER_STRUCTURAL":

        majorCard.classList.add(
          "major-danger"
        );

        break;


      // -15%超・Shockのみ
      case "LATE_ENTRY_CAUTION":

        majorCard.classList.add(
          "major-late"
        );

        break;


      // HOLD
      default:

        majorCard.classList.add(
          "major-low"
        );

        break;
    }

  })


  // ==========================
  // エラー処理
  // ==========================

  .catch(error => {

    console.error(
      "market.json 読み込みエラー:",
      error
    );

    const majorAction =
      document.getElementById(
        "majorAction"
      );

    const majorMessage =
      document.getElementById(
        "majorMessage"
      );

    if (majorAction) {

      majorAction.textContent =
        "⚠️ データ読み込みエラー";
    }

    if (majorMessage) {

      majorMessage.textContent =
        "market.jsonを読み込めませんでした。";
    }

  });