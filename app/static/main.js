// app/static/main.js
document.getElementById("send")?.addEventListener("click", async () => {
  const q = document.getElementById("question").value;
  if (!q) return alert("Please enter a question");
  document.getElementById("answer_text").textContent = "Thinking..."
  const res = await fetch("/api/query", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({question: q})
  });
  const j = await res.json();
  if (!j.ok) {
    document.getElementById("answer_text").textContent = "Error: " + (j.error || JSON.stringify(j));
    return;
  }
  const r = j.result;
  document.getElementById("answer_text").textContent = r.answer_text || "(no text)";
  const chartArea = document.getElementById("chart_area");
  chartArea.innerHTML = "";
  if (r.chart) {
    const img = document.createElement("img");
    img.src = r.chart;
    img.style.maxWidth = "800px";
    chartArea.appendChild(img);
  }
  document.getElementById("prov").textContent = JSON.stringify(r.provenance || {}, null, 2);
});
