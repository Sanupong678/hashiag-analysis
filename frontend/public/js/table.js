async function loadAllData() {
  const res = await fetch("http://localhost:5000/api/posts");
  const data = await res.json();
  renderTable(data);
}

function renderTable(posts) {
  const tbody = document.querySelector("#allDataTable tbody");
  tbody.innerHTML = "";
  posts.forEach(p => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><a href="${p.url}" target="_blank">${p.title}</a></td>
      <td>${p.subreddit}</td>
      <td>${p.score}</td>
      <td>${p.num_comments}</td>
      <td>${new Date(p.created_utc).toLocaleString()}</td>
    `;
    tbody.appendChild(tr);
  });
}

window.onload = loadAllData;
