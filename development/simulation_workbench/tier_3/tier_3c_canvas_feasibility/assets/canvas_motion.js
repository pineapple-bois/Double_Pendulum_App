(function () {
  "use strict";

  const canvasId = "tier3c-canvas";
  const state = {
    activeRunId: null,
    payload: null,
    frameIndex: 0,
    playing: false,
    rafHandle: null,
    playbackStartMs: 0,
    playbackStartFrame: 0,
    displayOptions: ["axes", "grid", "origin"],
    lastStatus: "No payload yet.",
  };

  function getCanvas() {
    return document.getElementById(canvasId);
  }

  function cancelLoop() {
    if (state.rafHandle !== null) {
      window.cancelAnimationFrame(state.rafHandle);
      state.rafHandle = null;
    }
    state.playing = false;
  }

  function payloadIsDrawable(payload) {
    return payload && payload.kind === "success" && payload.positions && payload.positions.x1;
  }

  function resizeCanvas(canvas) {
    const rect = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    const width = Math.max(1, Math.round(rect.width * ratio));
    const height = Math.max(1, Math.round(rect.height * ratio));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    return { width, height, ratio };
  }

  function clearCanvas(message) {
    const canvas = getCanvas();
    if (!canvas) {
      state.lastStatus = "Canvas element not found.";
      return state.lastStatus;
    }
    const metrics = resizeCanvas(canvas);
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, metrics.width, metrics.height);
    ctx.fillStyle = "#f8fafc";
    ctx.fillRect(0, 0, metrics.width, metrics.height);
    ctx.fillStyle = "#26364f";
    ctx.font = `${14 * metrics.ratio}px Arial, sans-serif`;
    ctx.textAlign = "center";
    ctx.fillText(message || "Canvas cleared.", metrics.width / 2, metrics.height / 2);
    state.lastStatus = message || "Canvas cleared.";
    return state.lastStatus;
  }

  function boundsFor(payload) {
    const bounds = payload.bounds || {};
    const minX = Number(bounds.min_x ?? -2);
    const maxX = Number(bounds.max_x ?? 2);
    const minY = Number(bounds.min_y ?? -2);
    const maxY = Number(bounds.max_y ?? 2);
    const xSpan = Math.max(0.001, maxX - minX);
    const ySpan = Math.max(0.001, maxY - minY);
    return { minX, maxX, minY, maxY, xSpan, ySpan };
  }

  function hasOption(name) {
    return Array.isArray(state.displayOptions) && state.displayOptions.includes(name);
  }

  function project(payload, x, y, metrics) {
    const bounds = boundsFor(payload);
    const margin = 30 * metrics.ratio;
    const drawableWidth = Math.max(1, metrics.width - 2 * margin);
    const drawableHeight = Math.max(1, metrics.height - 2 * margin);
    const scale = Math.min(drawableWidth / bounds.xSpan, drawableHeight / bounds.ySpan);
    const centerX = metrics.width / 2;
    const centerY = metrics.height / 2;
    const worldCenterX = (bounds.minX + bounds.maxX) / 2;
    const worldCenterY = (bounds.minY + bounds.maxY) / 2;
    return {
      x: centerX + (x - worldCenterX) * scale,
      y: centerY - (y - worldCenterY) * scale,
    };
  }

  function drawReferenceFrame(ctx, payload, metrics) {
    const bounds = boundsFor(payload);
    const minStep = Math.max(bounds.xSpan, bounds.ySpan) / 8;
    const magnitude = Math.pow(10, Math.floor(Math.log10(minStep)));
    const gridStep = Math.max(0.25, Math.ceil(minStep / magnitude) * magnitude);

    if (hasOption("grid")) {
      ctx.strokeStyle = "rgba(38, 54, 79, 0.10)";
      ctx.lineWidth = 1 * metrics.ratio;
      ctx.beginPath();
      for (let x = Math.ceil(bounds.minX / gridStep) * gridStep; x <= bounds.maxX; x += gridStep) {
        const a = project(payload, x, bounds.minY, metrics);
        const b = project(payload, x, bounds.maxY, metrics);
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
      }
      for (let y = Math.ceil(bounds.minY / gridStep) * gridStep; y <= bounds.maxY; y += gridStep) {
        const a = project(payload, bounds.minX, y, metrics);
        const b = project(payload, bounds.maxX, y, metrics);
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
      }
      ctx.stroke();
    }

    if (hasOption("axes")) {
      ctx.strokeStyle = "rgba(38, 54, 79, 0.38)";
      ctx.lineWidth = 1.5 * metrics.ratio;
      ctx.beginPath();
      const xAxisA = project(payload, bounds.minX, 0, metrics);
      const xAxisB = project(payload, bounds.maxX, 0, metrics);
      const yAxisA = project(payload, 0, bounds.minY, metrics);
      const yAxisB = project(payload, 0, bounds.maxY, metrics);
      ctx.moveTo(xAxisA.x, xAxisA.y);
      ctx.lineTo(xAxisB.x, xAxisB.y);
      ctx.moveTo(yAxisA.x, yAxisA.y);
      ctx.lineTo(yAxisB.x, yAxisB.y);
      ctx.stroke();

      ctx.fillStyle = "rgba(38, 54, 79, 0.75)";
      ctx.font = `${12 * metrics.ratio}px Arial, sans-serif`;
      ctx.textAlign = "left";
      ctx.fillText("+x", xAxisB.x - 18 * metrics.ratio, xAxisB.y - 6 * metrics.ratio);
      ctx.fillText("+y", yAxisB.x + 6 * metrics.ratio, yAxisB.y + 16 * metrics.ratio);
    }

    if (hasOption("origin")) {
      const origin = project(payload, 0, 0, metrics);
      ctx.strokeStyle = "#111827";
      ctx.fillStyle = "#ffffff";
      ctx.lineWidth = 2 * metrics.ratio;
      ctx.beginPath();
      ctx.arc(origin.x, origin.y, 5 * metrics.ratio, 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = "#111827";
      ctx.font = `${12 * metrics.ratio}px Arial, sans-serif`;
      ctx.textAlign = "left";
      ctx.fillText("pivot / origin", origin.x + 8 * metrics.ratio, origin.y - 8 * metrics.ratio);
    }
  }

  function drawFrame(frameIndex) {
    const canvas = getCanvas();
    const payload = state.payload;
    if (!canvas || !payloadIsDrawable(payload)) {
      return clearCanvas("No drawable motion payload.");
    }

    const positions = payload.positions;
    const sampleCount = Number(payload.sample_count || positions.x1.length || 0);
    const safeIndex = Math.max(0, Math.min(Number(frameIndex || 0), sampleCount - 1));
    state.frameIndex = safeIndex;

    const metrics = resizeCanvas(canvas);
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, metrics.width, metrics.height);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, metrics.width, metrics.height);
    drawReferenceFrame(ctx, payload, metrics);

    const origin = project(payload, 0, 0, metrics);
    const p1 = project(payload, positions.x1[safeIndex], positions.y1[safeIndex], metrics);
    const p2 = project(payload, positions.x2[safeIndex], positions.y2[safeIndex], metrics);

    ctx.strokeStyle = "rgba(68, 16, 173, 0.16)";
    ctx.lineWidth = 1 * metrics.ratio;
    ctx.beginPath();
    for (let i = 0; i <= safeIndex; i += Math.max(1, Math.floor(sampleCount / 400))) {
      const trail = project(payload, positions.x2[i], positions.y2[i], metrics);
      if (i === 0) {
        ctx.moveTo(trail.x, trail.y);
      } else {
        ctx.lineTo(trail.x, trail.y);
      }
    }
    ctx.stroke();

    ctx.strokeStyle = "#26364f";
    ctx.lineWidth = 3 * metrics.ratio;
    ctx.beginPath();
    ctx.moveTo(origin.x, origin.y);
    ctx.lineTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();

    ctx.fillStyle = "#F4762F";
    ctx.beginPath();
    ctx.arc(p1.x, p1.y, 7 * metrics.ratio, 0, 2 * Math.PI);
    ctx.fill();

    ctx.fillStyle = "#4EC5AE";
    ctx.beginPath();
    ctx.arc(p2.x, p2.y, 9 * metrics.ratio, 0, 2 * Math.PI);
    ctx.fill();

    ctx.fillStyle = "#1d2433";
    ctx.font = `${13 * metrics.ratio}px Arial, sans-serif`;
    ctx.textAlign = "left";
    const time = payload.time && payload.time[safeIndex] !== undefined ? payload.time[safeIndex].toFixed(3) : "?";
    ctx.fillText(`run ${payload.run_id} · frame ${safeIndex}/${sampleCount - 1} · t=${time}s`, 14 * metrics.ratio, 22 * metrics.ratio);
    ctx.fillText("physical x right; physical y up; screen y is inverted during rendering", 14 * metrics.ratio, 42 * metrics.ratio);
    ctx.fillText("equal physical scale on x/y", 14 * metrics.ratio, 62 * metrics.ratio);

    state.lastStatus = `run ${payload.run_id}; frame ${safeIndex}/${sampleCount - 1}; playing=${state.playing}`;
    return state.lastStatus;
  }

  function setPayload(payload) {
    const nextRunId = payload ? payload.run_id : null;
    const sameRun = nextRunId === state.activeRunId;
    if (nextRunId !== state.activeRunId) {
      cancelLoop();
      state.activeRunId = nextRunId;
      state.frameIndex = 0;
    }
    state.payload = payload;

    if (!payload) {
      return clearCanvas("No motion payload.");
    }
    if (payload.kind === "clear") {
      cancelLoop();
      return clearCanvas(`run ${payload.run_id}: cleared`);
    }
    if (payload.kind === "failure") {
      cancelLoop();
      return clearCanvas(`run ${payload.run_id}: simulated failure`);
    }
    return drawFrame(sameRun ? state.frameIndex : 0);
  }

  function play(payload) {
    if (payload && payload.run_id !== state.activeRunId) {
      setPayload(payload);
    }
    if (!payloadIsDrawable(state.payload)) {
      return clearCanvas("Cannot play without a successful motion payload.");
    }
    if (state.playing) {
      return state.lastStatus;
    }

    const runId = state.activeRunId;
    const sampleCount = Number(state.payload.sample_count || 0);
    const duration = Math.max(0.001, Number(state.payload.duration_seconds || 1));
    state.playing = true;
    state.playbackStartMs = performance.now();
    state.playbackStartFrame = state.frameIndex;

    function tick(now) {
      if (!state.playing || state.activeRunId !== runId) {
        cancelLoop();
        return;
      }
      const elapsedSeconds = (now - state.playbackStartMs) / 1000;
      const frameDelta = Math.floor((elapsedSeconds / duration) * sampleCount);
      const nextFrame = state.playbackStartFrame + frameDelta;
      if (nextFrame >= sampleCount - 1) {
        state.frameIndex = sampleCount - 1;
        drawFrame(state.frameIndex);
        cancelLoop();
        return;
      }
      drawFrame(nextFrame);
      state.rafHandle = window.requestAnimationFrame(tick);
    }

    state.rafHandle = window.requestAnimationFrame(tick);
    state.lastStatus = `run ${runId}; playback started`;
    return state.lastStatus;
  }

  function pause() {
    cancelLoop();
    drawFrame(state.frameIndex);
    return `run ${state.activeRunId}; paused at frame ${state.frameIndex}`;
  }

  function resetPlayback() {
    cancelLoop();
    state.frameIndex = 0;
    drawFrame(0);
    return `run ${state.activeRunId}; reset to frame 0`;
  }

  function scrub(frameIndex) {
    cancelLoop();
    drawFrame(frameIndex);
    return `run ${state.activeRunId}; scrubbed to frame ${state.frameIndex}`;
  }

  function handleCanvasEvent(payload, playClicks, pauseClicks, resetClicks, scrubValue, displayOptions) {
    void playClicks;
    void pauseClicks;
    void resetClicks;
    state.displayOptions = Array.isArray(displayOptions) ? displayOptions : [];
    const ctx = window.dash_clientside && window.dash_clientside.callback_context;
    const triggered = ctx && ctx.triggered && ctx.triggered.length ? ctx.triggered[0].prop_id.split(".")[0] : "";

    if (triggered === "tier3c-play") {
      return play(payload);
    }
    if (triggered === "tier3c-pause") {
      return pause();
    }
    if (triggered === "tier3c-reset-playback") {
      return resetPlayback();
    }
    if (triggered === "tier3c-scrubber") {
      return scrub(scrubValue || 0);
    }
    return setPayload(payload);
  }

  function emptyFigure(title, message) {
    return {
      data: [],
      layout: {
        title,
        height: 320,
        margin: { l: 48, r: 20, t: 48, b: 44 },
        annotations: [
          {
            text: message,
            showarrow: false,
            xref: "paper",
            yref: "paper",
            x: 0.5,
            y: 0.5,
          },
        ],
      },
    };
  }

  function markerIndex(payload, scrubValue) {
    if (!payloadIsDrawable(payload)) {
      return 0;
    }
    const sampleCount = Number(payload.sample_count || 0);
    return Math.max(0, Math.min(Number(scrubValue || 0), sampleCount - 1));
  }

  function inspectionFigures(payload, scrubValue) {
    if (!payloadIsDrawable(payload) || !payload.angular_state) {
      const emptyTime = emptyFigure("Angular displacement time series", "Run a successful simulation to inspect angular state.");
      const emptyProjection = emptyFigure("Theta-theta angular state projection", "Run a successful simulation to inspect the projection.");
      return [emptyTime, emptyProjection, "No selected state."];
    }

    const index = markerIndex(payload, scrubValue);
    const time = payload.time || [];
    const theta1 = payload.angular_state.theta1_deg || [];
    const theta2 = payload.angular_state.theta2_deg || [];
    const selectedTime = Number(time[index] || 0);
    const selectedTheta1 = Number(theta1[index] || 0);
    const selectedTheta2 = Number(theta2[index] || 0);

    const timeFigure = {
      data: [
        { x: time, y: theta1, type: "scatter", mode: "lines", name: "theta1", line: { color: "#F4762F", width: 2 } },
        { x: time, y: theta2, type: "scatter", mode: "lines", name: "theta2", line: { color: "#4EC5AE", width: 2 } },
        { x: [selectedTime], y: [selectedTheta1], type: "scatter", mode: "markers", name: "selected theta1", marker: { color: "#9B1B30", size: 10 } },
        { x: [selectedTime], y: [selectedTheta2], type: "scatter", mode: "markers", name: "selected theta2", marker: { color: "#006D77", size: 10 } },
      ],
      layout: {
        title: "Angular displacement time series",
        height: 320,
        margin: { l: 52, r: 20, t: 48, b: 48 },
        xaxis: { title: "Time / seconds", zeroline: false },
        yaxis: { title: "Angular displacement / degrees", zeroline: false },
        shapes: [
          {
            type: "line",
            x0: selectedTime,
            x1: selectedTime,
            y0: 0,
            y1: 1,
            xref: "x",
            yref: "paper",
            line: { color: "#26364f", width: 1, dash: "dot" },
          },
        ],
        showlegend: true,
      },
    };

    const projectionFigure = {
      data: [
        { x: theta1, y: theta2, type: "scatter", mode: "lines", name: "theta-theta projection", line: { color: "#4410AD", width: 2 } },
        { x: [selectedTheta1], y: [selectedTheta2], type: "scatter", mode: "markers", name: "selected state", marker: { color: "#F4762F", size: 11 } },
      ],
      layout: {
        title: "Theta-theta angular state projection",
        height: 320,
        margin: { l: 52, r: 20, t: 48, b: 48 },
        xaxis: { title: "theta1 / degrees", zeroline: false },
        yaxis: { title: "theta2 / degrees", zeroline: false },
        showlegend: true,
      },
    };

    const readout = [
      `run ${payload.run_id}`,
      `frame ${index}/${payload.sample_count - 1}`,
      `t=${selectedTime.toFixed(4)}s`,
      `theta1=${selectedTheta1.toFixed(3)} deg`,
      `theta2=${selectedTheta2.toFixed(3)} deg`,
      `Canvas and Plotly markers share the scrubber-selected frame.`,
      `Playback marker sync is deferred; scrub sync is implemented.`,
    ].join("\n");

    return [timeFigure, projectionFigure, readout];
  }

  window.tier3cCanvasManager = {
    handleCanvasEvent,
    state,
  };

  window.dash_clientside = Object.assign({}, window.dash_clientside, {
    tier3c_canvas: {
      handleCanvasEvent,
      inspectionFigures,
    },
  });
})();
