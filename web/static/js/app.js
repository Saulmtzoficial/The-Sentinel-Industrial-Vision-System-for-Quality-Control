// Sistema Vision - JavaScript Principal

// Socket.IO
const socket = io();

// Gráficos
let graficoCalidadTiempoReal;
let graficoHorario;

// Estado
let estadoActual = "detenido";

// ==================== CHART.JS — TEMA OSCURO GLOBAL ====================
Chart.defaults.color = "#555962";
Chart.defaults.borderColor = "rgba(255,255,255,0.04)";
Chart.defaults.backgroundColor = "rgba(59,130,246,0.06)";

// ==================== INICIALIZACIÓN ====================

document.addEventListener("DOMContentLoaded", function () {
  console.log("Sistema Vision iniciado");

  inicializarGraficos();
  inicializarEventListeners();
  inicializarReloj();
  cargarDatosIniciales();

  socket.on("connect", function () {
    console.log("WebSocket conectado");
    mostrarNotificacion("Conectado al sistema", "success");
  });

  socket.on("disconnect", function () {
    console.log("WebSocket desconectado");
    mostrarNotificacion("Desconectado del sistema", "warning");
  });

  socket.on("estadisticas", actualizarEstadisticas);
  socket.on("graficos", actualizarGraficos);
  socket.on("nuevo_evento", agregarEvento);
  socket.on("nueva_alarma", agregarAlarma);
  socket.on("cambio_estado", actualizarEstado);
});

// ==================== GRÁFICOS ====================

function inicializarGraficos() {
  // ── Gráfico de Calidad en Tiempo Real ──
  const ctxCalidad = document
    .getElementById("grafico-calidad-tiempo-real")
    .getContext("2d");
  graficoCalidadTiempoReal = new Chart(ctxCalidad, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Calidad (%)",
          data: [],
          borderColor: "#06b6d4",
          backgroundColor: "rgba(6,182,212,0.06)",
          borderWidth: 1.5,
          tension: 0.4,
          fill: true,
          pointRadius: 0,
          pointHitRadius: 10,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: "index",
          intersect: false,
          backgroundColor: "rgba(18,21,28,0.95)",
          borderColor: "rgba(255,255,255,0.08)",
          borderWidth: 1,
          titleColor: "#8b8f9a",
          bodyColor: "#e4e6eb",
          titleFont: { family: "'JetBrains Mono', monospace", size: 11 },
          bodyFont: { family: "'DM Sans', sans-serif", size: 13 },
          callbacks: {
            label: (ctx) => ` ${ctx.parsed.y.toFixed(1)}%`,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          grid: {
            color: "rgba(255,255,255,0.03)",
            drawBorder: false,
          },
          ticks: {
            color: "#555962",
            font: { family: "'JetBrains Mono', monospace", size: 10 },
            callback: (v) => v + "%",
          },
        },
        x: { display: false },
      },
      animation: { duration: 600 },
    },
  });

  // ── Gráfico Horario ──
  const ctxHorario = document
    .getElementById("grafico-horario")
    .getContext("2d");
  graficoHorario = new Chart(ctxHorario, {
    type: "bar",
    data: {
      labels: [],
      datasets: [
        {
          label: "Aceptadas",
          data: [],
          backgroundColor: "rgba(34,197,94,0.2)",
          borderColor: "rgba(34,197,94,0.5)",
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: "Rechazadas",
          data: [],
          backgroundColor: "rgba(239,68,68,0.15)",
          borderColor: "rgba(239,68,68,0.4)",
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: {
            color: "#555962",
            font: { family: "'DM Sans', sans-serif", size: 12 },
            boxWidth: 10,
            padding: 16,
          },
        },
        tooltip: {
          mode: "index",
          intersect: false,
          backgroundColor: "rgba(18,21,28,0.95)",
          borderColor: "rgba(255,255,255,0.08)",
          borderWidth: 1,
          titleColor: "#8b8f9a",
          bodyColor: "#e4e6eb",
          titleFont: { family: "'JetBrains Mono', monospace", size: 11 },
          bodyFont: { family: "'DM Sans', sans-serif", size: 13 },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: "rgba(255,255,255,0.03)", drawBorder: false },
          ticks: {
            stepSize: 1,
            color: "#555962",
            font: { family: "'JetBrains Mono', monospace", size: 10 },
          },
        },
        x: {
          grid: { color: "rgba(255,255,255,0.02)", drawBorder: false },
          ticks: {
            color: "#555962",
            font: { family: "'JetBrains Mono', monospace", size: 10 },
          },
        },
      },
    },
  });
}

// ==================== EVENT LISTENERS ====================

function inicializarEventListeners() {
  document
    .getElementById("btn-iniciar")
    .addEventListener("click", iniciarSistema);
  document
    .getElementById("btn-detener")
    .addEventListener("click", detenerSistema);
  document
    .getElementById("btn-resetear-contadores")
    .addEventListener("click", resetearContadores);

}

// ==================== CONTROL DEL SISTEMA ====================

function iniciarSistema() {
  fetch("/api/control/iniciar", { method: "POST" })
    .then((r) => r.json())
    .then((data) => {
      mostrarNotificacion(
        data.msg || "Sistema iniciado",
        data.status === "ok" ? "success" : "warning",
      );
    })
    .catch(() => mostrarNotificacion("Error al iniciar sistema", "danger"));
}

function detenerSistema() {
  fetch("/api/control/detener", { method: "POST" })
    .then((r) => r.json())
    .then((data) => mostrarNotificacion(data.msg || "Sistema detenido", "info"))
    .catch(() => mostrarNotificacion("Error al detener sistema", "danger"));
}

function resetearContadores() {
  if (confirm("¿Está seguro de resetear todos los contadores?")) {
    fetch("/api/contadores/reset", { method: "POST" })
      .then((r) => r.json())
      .then((data) =>
        mostrarNotificacion(data.msg || "Contadores reseteados", "info"),
      )
      .catch(() =>
        mostrarNotificacion("Error al resetear contadores", "danger"),
      );
  }
}

// ==================== ACTUALIZACIÓN DE DATOS ====================

function cargarDatosIniciales() {
  fetch("/api/estadisticas")
    .then((r) => r.json())
    .then(actualizarEstadisticas)
    .catch(console.error);
  fetch("/api/graficos")
    .then((r) => r.json())
    .then(actualizarGraficos)
    .catch(console.error);
  fetch("/api/eventos")
    .then((r) => r.json())
    .then((ev) => ev.reverse().forEach(agregarEvento))
    .catch(console.error);
  fetch("/api/alarmas")
    .then((r) => r.json())
    .then((al) => al.forEach(agregarAlarma))
    .catch(console.error);
}

function actualizarEstadisticas(data) {
  document.getElementById("contador-inspeccionadas").textContent =
    data.contadores?.inspeccionadas ?? 0;
  document.getElementById("contador-aceptadas").textContent =
    data.contadores?.aceptadas ?? 0;
  document.getElementById("contador-rechazadas").textContent =
    data.contadores?.rechazadas ?? 0;
  document.getElementById("tuercas-ok").textContent =
    data.contadores?.tuercas_ok ?? 0;
  document.getElementById("tuercas-nok").textContent =
    data.contadores?.tuercas_nok ?? 0;
  document.getElementById("tornillos-ok").textContent =
    data.contadores?.tornillos_ok ?? 0;
  document.getElementById("tornillos-nok").textContent =
    data.contadores?.tornillos_nok ?? 0;
  document.getElementById("calidad-actual").textContent =
    (data.calidad_actual ?? 100).toFixed(1) + "%";
  document.getElementById("fps-navbar").textContent = data.fps ?? 0;
  actualizarEstado({ estado: data.estado ?? "detenido" });
}

function actualizarGraficos(data) {
  if (data.calidad_tiempo_real?.length > 0) {
    graficoCalidadTiempoReal.data.labels = data.calidad_tiempo_real.map(
      (_, i) => i,
    );
    graficoCalidadTiempoReal.data.datasets[0].data =
      data.calidad_tiempo_real.map((i) => i.calidad);
    graficoCalidadTiempoReal.update("none");
  }

  if (data.metricas_horarias?.length > 0) {
    graficoHorario.data.labels = data.metricas_horarias.map((i) => i.hora);
    graficoHorario.data.datasets[0].data = data.metricas_horarias.map(
      (i) => i.aceptadas,
    );
    graficoHorario.data.datasets[1].data = data.metricas_horarias.map(
      (i) => i.rechazadas,
    );
    graficoHorario.update("none");
  }
}

function actualizarEstado(data) {
  estadoActual = data.estado;
  const badge = document.getElementById("badge-estado");
  const texto = document.getElementById("texto-estado");

  if (data.estado === "en_ejecucion") {
    badge.classList.add("running");
    texto.textContent = "En ejecución";
  } else {
    badge.classList.remove("running");
    texto.textContent = "Detenido";
  }
}

// ==================== EVENTOS Y ALARMAS ====================

function agregarEvento(evento) {
  const container = document.getElementById("eventos-container");
  const div = document.createElement("div");
  div.className = "evento-item";

  const timestamp = new Date(evento.timestamp).toLocaleTimeString("es-MX");
  const icons = {
    success: "fa-check-circle",
    warning: "fa-exclamation-triangle",
    error: "fa-times-circle",
    info: "fa-info-circle",
  };
  const iconClass = icons[evento.tipo] ?? "fa-info-circle";

  div.innerHTML = `
    <div class="evento-timestamp">${timestamp}</div>
    <div class="evento-mensaje">
      <i class="fas ${iconClass} evento-icon evento-${evento.tipo ?? "info"}"></i>
      ${evento.mensaje}
    </div>`;

  container.insertBefore(div, container.firstChild);
  while (container.children.length > 100)
    container.removeChild(container.lastChild);
}

function agregarAlarma(alarma) {
  const container = document.getElementById("alarmas-container");
  if (container.querySelector(".alert-success")) container.innerHTML = "";

  const div = document.createElement("div");
  div.className = `alarma-item alarma-${alarma.tipo}`;
  div.id = `alarma-${alarma.id}`;

  const timestamp = new Date(alarma.timestamp).toLocaleTimeString("es-MX");
  div.innerHTML = `
    <div class="alarma-content">
      <div class="alarma-timestamp">${timestamp}</div>
      <div><strong>${alarma.mensaje}</strong></div>
    </div>
    <button class="btn btn-sm btn-limpiar-alarma" onclick="limpiarAlarma(${alarma.id})">
      <i class="fas fa-times"></i>
    </button>`;

  container.insertBefore(div, container.firstChild);
  actualizarContadorAlarmas();
}

function limpiarAlarma(alarmaId) {
  fetch(`/api/alarmas/limpiar/${alarmaId}`, { method: "POST" })
    .then((r) => r.json())
    .then((data) => {
      if (data.success) {
        document.getElementById(`alarma-${alarmaId}`)?.remove();
        actualizarContadorAlarmas();
      }
    })
    .catch(console.error);
}

function actualizarContadorAlarmas() {
  const container = document.getElementById("alarmas-container");
  const count = container.querySelectorAll(".alarma-item").length;
  document.getElementById("contador-alarmas").textContent = count;
  if (count === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <i class="fas fa-check-circle"></i> Sin alarmas
      </div>`;
  }
}

// ==================== UTILIDADES ====================

function mostrarNotificacion(mensaje, tipo = "info") {
  const n = document.createElement("div");
  n.className = `alert alert-${tipo} alert-dismissible fade show notification`;
  n.innerHTML = `${mensaje}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
  document.body.appendChild(n);
  setTimeout(() => n.remove(), 5000);
}

function inicializarReloj() {
  const actualizar = () => {
    document.getElementById("reloj").textContent =
      new Date().toLocaleTimeString("es-MX", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });
  };
  actualizar();
  setInterval(actualizar, 1000);
}

// ==================== MANEJO DE ERRORES ====================

window.addEventListener("error", (e) =>
  console.error("Error global:", e.error),
);

document
  .getElementById("video-stream")
  .addEventListener("error", () => {
    mostrarNotificacion(
      "Error en el stream de video. Intentando reconectar...",
      "warning",
    );
    // Reconectar stream MJPEG
    setTimeout(() => {
      document.getElementById("video-stream").src = "/video_feed?" + Date.now();
    }, 3000);
  });
