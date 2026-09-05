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
    document.getElementById("risk").textContent = "市場リスク：" + data.risk;
    document.getElementById("sp500").textContent = "S&P500連動ETF(SPY)： " + data.sp500;
    document.getElementById("vix").textContent = "VIX： " + data.vix;
  })
  .catch(error => {
    console.error("データの読み込みに失敗しました", error);
  });
