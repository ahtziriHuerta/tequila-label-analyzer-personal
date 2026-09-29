const API = "http://127.0.0.1:8000";

// "Hola mundo conectado": verifica que el frontend habla con el backend.
fetch(`${API}/salud`)
  .then(r => r.json())
  .then(d => document.getElementById("estado-api").textContent = `Backend: ${d.estado}`)
  .catch(() => document.getElementById("estado-api").textContent = "Backend no disponible");
