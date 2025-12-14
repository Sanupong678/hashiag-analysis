// ============================
// 📊 chart.js (รวมฟังก์ชัน Dashboard + Compare)
// ============================

// --- Trending Keywords Chart ---
let trendChartInstance;

function renderTrendChart(trends, onKeywordClick) {
  const ctx = document.getElementById("trendChart").getContext("2d");

  if (trendChartInstance) trendChartInstance.destroy();

  const labels = trends.map(item => item.keyword || item._id);
  const values = trends.map(item => item.count || item.post_count);

  trendChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "จำนวนโพสต์",
        data: values,
        backgroundColor: "rgba(54, 162, 235, 0.6)",
        borderColor: "rgba(54, 162, 235, 1)",
        borderWidth: 1,
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        title: {
          display: true,
          text: "Trending Keywords (คลิกแท่งเพื่อดูโพสต์)",
          font: { size: 18 },
        },
      },
      onClick: (evt, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const keyword = labels[index];
          onKeywordClick(keyword);
        }
      },
    },
  });
}

// --- Compare Keywords Chart ---
let compareChartInstance;

function renderCompareChart(data) {
  const ctx = document.getElementById("compareChart").getContext("2d");

  if (compareChartInstance) compareChartInstance.destroy();

  const datasets = data.series.map(item => ({
    label: item.keyword,
    data: item.values,
    borderColor: item.color,
    backgroundColor: item.color + "55",
    fill: false,
    tension: 0.3,
  }));

  compareChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.dates,
      datasets,
    },
    options: {
      responsive: true,
      plugins: {
        title: {
          display: true,
          text: "Keyword Comparison Over Time",
          font: { size: 18 },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: "จำนวนโพสต์ต่อวัน" },
        },
        x: {
          title: { display: true, text: "วันที่ (UTC)" },
        },
      },
    },
  });
}
