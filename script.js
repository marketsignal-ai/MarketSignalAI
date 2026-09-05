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

  })
  .catch(error => {
    console.error("market.json 読み込みエラー:", error);
  });
