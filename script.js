// ==========================
// Market Signal AI
// Version 0.2
// ==========================

// ダミーの市場データ
const marketData = {
    weather: "☀️ 晴れ",
    risk: "低",
    action: "積立継続",
    comment: "市場は健全です。今週は何もしなくて大丈夫です。"
};

console.log("Market Signal AI 起動");
console.log(marketData);

document.getElementById("weather").textContent
document.getElementById("risk").textContent

function changeWeather(type) {

    const weather = document.getElementById("weather");
    const risk = document.getElementById("risk");

    if (type === "sunny") {
        weather.textContent = "☀️ 晴れ";
        risk.textContent = "市場リスク：低";
    }

    if (type === "cloudy") {
        weather.textContent = "☁️ 曇り";
        risk.textContent = "市場リスク：中";
    }

    if (type === "rain") {
        weather.textContent = "🌧 雨";
        risk.textContent = "市場リスク：高";
    }
}

fetch("market.json")
  .then(response => response.json())
  .then(data => {

    document.getElementById("weather").textContent = data.weather;
    document.getElementById("risk").textContent = data.risk;

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
      "ハイイールド債スプレッド： " + data.high_yield_spread + "%";

    document.getElementById("initial_claims").textContent =
      "新規失業保険申請件数： " +
       Number(data.initial_claims).toLocaleString() + "件";  

    const vixElement = document.getElementById("vix");
    const diffElement = document.getElementById("sp500_200ma_diff");

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
// ===== Market Risk Score =====

let score = 0;
let reasons = [];

// VIX
if (data.vix >= 30) {
  score += 3;
  reasons.push("VIXが30以上");
} else if (data.vix >= 25) {
  score += 2;
  reasons.push("VIXが25以上");
} else if (data.vix >= 20) {
  score += 1;
  reasons.push("VIXが20以上");
}

// S&P500と200日移動平均
if (data.sp500_200ma_diff <= -10) {
  score += 3;
  reasons.push("S&P500が200日線を10%以上下回る");
} else if (data.sp500_200ma_diff <= -5) {
  score += 2;
  reasons.push("S&P500が200日線を5%以上下回る");
} else if (data.sp500_200ma_diff < 0) {
  score += 1;
  reasons.push("S&P500が200日線を下回る");
}

// ハイイールド債スプレッド
if (data.high_yield_spread >= 6) {
  score += 3;
  reasons.push("信用市場のストレスが非常に高い");
} else if (data.high_yield_spread >= 5) {
  score += 2;
  reasons.push("信用市場のストレスが高い");
} else if (data.high_yield_spread >= 4) {
  score += 1;
  reasons.push("信用市場に警戒感");
}


// ===== 総合判定 =====

let weather;
let risk;
let comment;
let action1;
let action2;

if (score >= 7) {
  weather = "⛈️ 危険";
  risk = "非常に高い";
  comment =
    "複数の市場指標が強い警戒シグナルを示しています。";

  action1 = "新規投資は慎重に";
  action2 = "売買判断は急がず確認";

} else if (score >= 5) {
  weather = "🌧️ 警戒";
  risk = "高い";
  comment =
    "市場ストレスが高まっています。値動きに注意してください。";

  action1 = "積立は継続";
  action2 = "追加投資は慎重に";

} else if (score >= 3) {
  weather = "☁️ 注意";
  risk = "中程度";
  comment =
    "一部の指標に警戒シグナルが出ています。";

  action1 = "積立継続";
  action2 = "市場の変化を確認";

} else {
  weather = "☀️ 晴れ";
  risk = "低い";
  comment =
    "主要な市場ストレス指標は現在落ち着いています。";

  action1 = "積立継続";
  action2 = "売却不要";
}

// ===== 画面表示 =====

document.getElementById("weather").textContent = weather;

document.getElementById("risk").textContent =
  "市場リスク：" + risk;

document.getElementById("riskScore").textContent =
  "Market Risk Score： " + score + " / 9";

document.getElementById("action1").textContent =
  action1;

document.getElementById("action2").textContent =
  action2;

document.getElementById("aiComment").textContent =
  comment;

})
.catch(error => {
  console.error("market.json 読み込みエラー:", error);
});
