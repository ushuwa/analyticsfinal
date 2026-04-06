let map = L.map('map').setView([12.8797,121.7740], 6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

fetch("/ppi/heatmap-data").then(r=>r.json()).then(data=>{
  data.forEach(d=>{
    let color = d.ppi_score > 50 ? "green" : "red";
    L.circle([d.lat, d.lng], {radius:30000, color, fillOpacity:0.4}).addTo(map);
  });
});

fetch("/ppi/trend-data").then(r=>r.json()).then(d=>{
  new Chart(document.getElementById("trend"), {
    type:"line",
    data:{ labels:d.labels, datasets:[{label:"Poverty Likelihood", data:d.values}] }
  });
});

fetch("/ppi/prepost-data").then(r=>r.json()).then(d=>{
  new Chart(document.getElementById("prepost"), {
    type:"bar",
    data:{
      labels:["Pre","Post"],
      datasets:[
        {label:"Pre", data:d.pre},
        {label:"Post", data:d.post}
      ]
    }
  });
});

function calc(){
  let a = parseFloat(document.getElementById("a").value || 0);
  let b = parseFloat(document.getElementById("b").value || 0);

  fetch("/ppi/calculator", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({a,b})
  })
  .then(r=>r.json())
  .then(j=>{
    document.getElementById("out").innerText = JSON.stringify(j);
  });
}
