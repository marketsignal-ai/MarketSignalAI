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

// 急変スコアを加算
score += Number(data.sudden_score || 0);

// ===== 総合判定 =====

let weather;
let risk;
let comment;
let action1;
let action2;

if (score >= 10) {
  weather = "⛈️ 危険";
  risk = "非常に高い";
  comment =
    "複数の市場指標と急変シグナルが強い警戒状態を示しています。";

  action1 = "新規投資は慎重に";
  action2 = "売買判断は急がず確認";

} else if (score >= 7) {
  weather = "🌧️ 警戒";
  risk = "高い";
  comment =
    "市場ストレスまたは急変シグナルが高まっています。";

  action1 = "積立は継続";
  action2 = "追加投資は慎重に";

} else if (score >= 4) {
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
  "Market Risk Score： " + score + " / 15";

document.getElementById("suddenScore").textContent =
  "急変スコア： " + data.sudden_score + " / 6";  

const suddenElement = document.getElementById("suddenScore");

if (data.sudden_score <= 1) {
  suddenElement.style.color = "green";
} else if (data.sudden_score <= 3) {
  suddenElement.style.color = "orange";
} else {
  suddenElement.style.color = "red";
}  


const suddenElement = document.getElementById("suddenScore");

if (data.sudden_score <= 1) {
  suddenElement.style.color = "green";
} else if (data.sudden_score <= 3) {
  suddenElement.style.color = "orange";
} else {
  suddenElement.style.color = "red";
}  

document.getElementById("action1").textContent =
  action1;

document.getElementById("action2").textContent =
  action2;

document.getElementById("aiComment").textContent =
  comment;

// ===== 判定理由 =====

let reasonText = "";

if (reasons.length === 0) {
  reasonText =
    "・VIXは安定しています\n" +
    "・S&P500は200日移動平均線より上です\n" +
    "・ハイイールド債スプレッドは低水準です";
} else {
  reasonText = reasons
    .map(reason => "・" + reason)
    .join("\n");
}

document.getElementById("riskReasons").textContent =
  reasonText;

// ===== 市場状況 =====

// 市場トレンド
let trendStatus;

if (data.sp500_200ma_diff >= 0) {
  trendStatus = "🟢 市場トレンド";
} else if (data.sp500_200ma_diff >= -5) {
  trendStatus = "🟡 市場トレンド";
} else {
  trendStatus = "🔴 市場トレンド";
}


// 市場心理
let sentimentStatus;

if (data.vix < 20) {
  sentimentStatus = "🟢 市場心理";
} else if (data.vix < 30) {
  sentimentStatus = "🟡 市場心理";
} else {
  sentimentStatus = "🔴 市場心理";
}


// 景気
let economyStatus;

if (
  data.yield_curve >= 0 &&
  data.initial_claims < 300000
) {
  economyStatus = "🟢 景気";
} else if (
  data.yield_curve >= -0.5 &&
  data.initial_claims < 350000
) {
  economyStatus = "🟡 景気";
} else {
  economyStatus = "🔴 景気";
}


// 為替
let fxStatus;

if (data.usdjpy < 150) {
  fxStatus = "🟢 為替";
} else if (data.usdjpy < 160) {
  fxStatus = "🟡 為替";
} else {
  fxStatus = "🔴 為替";
}


// 画面に表示
document.getElementById("trendStatus").textContent =
  trendStatus;

document.getElementById("sentimentStatus").textContent =
  sentimentStatus;

document.getElementById("economyStatus").textContent =
  economyStatus;

document.getElementById("fxStatus").textContent =
  fxStatus;


})
.catch(error => {
  console.error("market.json 読み込みエラー:", error);
});
