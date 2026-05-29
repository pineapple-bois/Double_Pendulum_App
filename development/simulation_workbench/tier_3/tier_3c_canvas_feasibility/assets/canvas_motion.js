(function () {
  "use strict";

  const canvasIds = {
    motion: "tier3c-canvas",
    timeSeries: "tier3c-time-series-canvas",
    projection: "tier3c-projection-canvas",
  };

  const state = {
    activeRunId: null,
    payload: null,
    frameIndex: 0,
    playing: false,
    rafHandle: null,
    playbackStartMs: 0,
    playbackStartFrame: 0,
    displayOptions: ["axes", "grid"],
    lastStatus: "No payload yet.",
  };

  function getCanvas(name) {
    return document.getElementById(canvasIds[name]);
  }

  function cancelLoop() {
    if (state.rafHandle !== null) {
      window.cancelAnimationFrame(state.rafHandle);
      state.rafHandle = null;
    }
    state.playing = false;
  }

  function payloadIsDrawable(payload) {
    return payload && payload.kind === "success" && payload.positions && payload.positions.x1 && payload.angular_state;
  }

  function hasOption(name) {
    return Array.isArray(state.displayOptions) && state.displayOptions.includes(name);
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

  function contextFor(name) {
    const canvas = getCanvas(name);
    if (!canvas) {
      return null;
    }
    const metrics = resizeCanvas(canvas);
    return { canvas, ctx: canvas.getContext("2d"), metrics };
  }

  function clearPanel(name, message) {
    const target = contextFor(name);
    if (!target) {
      return;
    }
    const { ctx, metrics } = target;
    ctx.clearRect(0, 0, metrics.width, metrics.height);
    ctx.fillStyle = "#f8fafc";
    ctx.fillRect(0, 0, metrics.width, metrics.height);
    ctx.fillStyle = "#26364f";
    ctx.font = `${14 * metrics.ratio}px Arial, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(message || "No data.", metrics.width / 2, metrics.height / 2);
  }

  function clearAll(message) {
    clearPanel("motion", message);
    clearPanel("timeSeries", message);
    clearPanel("projection", message);
    state.lastStatus = message || "Canvas panels cleared.";
    const statusEl = document.getElementById("tier3c-canvas-status");
    const readoutEl = document.getElementById("tier3c-selected-readout");
    if (statusEl) {
      statusEl.innerText = state.lastStatus;
    }
    if (readoutEl) {
      readoutEl.innerText = "No selected state.";
    }
    return [state.lastStatus, "No selected state."];
  }

  function arrayBounds(values, paddingRatio) {
    let min = Infinity;
    let max = -Infinity;
    for (const value of values || []) {
      const number = Number(value);
      if (Number.isFinite(number)) {
        min = Math.min(min, number);
        max = Math.max(max, number);
      }
    }
    if (!Number.isFinite(min) || !Number.isFinite(max)) {
      return { min: -1, max: 1, span: 2 };
    }
    if (min === max) {
      min -= 1;
      max += 1;
    }
    const span = max - min;
    const padding = Math.max(0.001, span * (paddingRatio || 0.08));
    return { min: min - padding, max: max + padding, span: span + 2 * padding };
  }

  function motionBounds(payload) {
    const bounds = payload.bounds || {};
    const minX = Number(bounds.min_x ?? -2);
    const maxX = Number(bounds.max_x ?? 2);
    const minY = Number(bounds.min_y ?? -2);
    const maxY = Number(bounds.max_y ?? 2);
    return {
      minX,
      maxX,
      minY,
      maxY,
      xSpan: Math.max(0.001, maxX - minX),
      ySpan: Math.max(0.001, maxY - minY),
    };
  }

  function motionProject(payload, x, y, metrics) {
    const bounds = motionBounds(payload);
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

  function plotArea(metrics) {
    return {
      left: 48 * metrics.ratio,
      right: metrics.width - 18 * metrics.ratio,
      top: 32 * metrics.ratio,
      bottom: metrics.height - 38 * metrics.ratio,
    };
  }

  function plotProject(x, y, xBounds, yBounds, area) {
    const xRatio = (x - xBounds.min) / xBounds.span;
    const yRatio = (y - yBounds.min) / yBounds.span;
    return {
      x: area.left + xRatio * (area.right - area.left),
      y: area.bottom - yRatio * (area.bottom - area.top),
    };
  }

  function drawPlotReference(ctx, metrics, area, xLabel, yLabel) {
    ctx.strokeStyle = "rgba(38, 54, 79, 0.45)";
    ctx.lineWidth = 1.2 * metrics.ratio;
    ctx.strokeRect(area.left, area.top, area.right - area.left, area.bottom - area.top);

    if (hasOption("grid")) {
      ctx.strokeStyle = "rgba(38, 54, 79, 0.10)";
      ctx.lineWidth = 1 * metrics.ratio;
      ctx.beginPath();
      for (let i = 1; i < 5; i++) {
        const x = area.left + (i / 5) * (area.right - area.left);
        const y = area.top + (i / 5) * (area.bottom - area.top);
        ctx.moveTo(x, area.top);
        ctx.lineTo(x, area.bottom);
        ctx.moveTo(area.left, y);
        ctx.lineTo(area.right, y);
      }
      ctx.stroke();
    }

    if (hasOption("axes")) {
      ctx.fillStyle = "rgba(38, 54, 79, 0.78)";
      ctx.font = `${12 * metrics.ratio}px Arial, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(xLabel, (area.left + area.right) / 2, metrics.height - 13 * metrics.ratio);
      ctx.save();
      ctx.translate(13 * metrics.ratio, (area.top + area.bottom) / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText(yLabel, 0, 0);
      ctx.restore();
    }
  }

  function drawMotionReference(ctx, payload, metrics) {
    const bounds = motionBounds(payload);
    const minStep = Math.max(bounds.xSpan, bounds.ySpan) / 8;
    const magnitude = Math.pow(10, Math.floor(Math.log10(minStep)));
    const gridStep = Math.max(0.25, Math.ceil(minStep / magnitude) * magnitude);

    if (hasOption("grid")) {
      ctx.strokeStyle = "rgba(38, 54, 79, 0.10)";
      ctx.lineWidth = 1 * metrics.ratio;
      ctx.beginPath();
      for (let x = Math.ceil(bounds.minX / gridStep) * gridStep; x <= bounds.maxX; x += gridStep) {
        const a = motionProject(payload, x, bounds.minY, metrics);
        const b = motionProject(payload, x, bounds.maxY, metrics);
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
      }
      for (let y = Math.ceil(bounds.minY / gridStep) * gridStep; y <= bounds.maxY; y += gridStep) {
        const a = motionProject(payload, bounds.minX, y, metrics);
        const b = motionProject(payload, bounds.maxX, y, metrics);
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
      }
      ctx.stroke();
    }

    if (hasOption("axes")) {
      ctx.strokeStyle = "rgba(38, 54, 79, 0.36)";
      ctx.lineWidth = 1.4 * metrics.ratio;
      const xAxisA = motionProject(payload, bounds.minX, 0, metrics);
      const xAxisB = motionProject(payload, bounds.maxX, 0, metrics);
      const yAxisA = motionProject(payload, 0, bounds.minY, metrics);
      const yAxisB = motionProject(payload, 0, bounds.maxY, metrics);
      ctx.beginPath();
      ctx.moveTo(xAxisA.x, xAxisA.y);
      ctx.lineTo(xAxisB.x, xAxisB.y);
      ctx.moveTo(yAxisA.x, yAxisA.y);
      ctx.lineTo(yAxisB.x, yAxisB.y);
      ctx.stroke();

      ctx.fillStyle = "rgba(38, 54, 79, 0.72)";
      ctx.font = `${12 * metrics.ratio}px Arial, sans-serif`;
      ctx.textAlign = "left";
      ctx.textBaseline = "alphabetic";
      ctx.fillText("+x", xAxisB.x - 18 * metrics.ratio, xAxisB.y - 6 * metrics.ratio);
      ctx.fillText("+y", yAxisB.x + 6 * metrics.ratio, yAxisB.y + 16 * metrics.ratio);
    }

    const pivot = motionProject(payload, 0, 0, metrics);
    ctx.strokeStyle = "#111827";
    ctx.fillStyle = "#ffffff";
    ctx.lineWidth = 2 * metrics.ratio;
    ctx.beginPath();
    ctx.arc(pivot.x, pivot.y, 5 * metrics.ratio, 0, 2 * Math.PI);
    ctx.fill();
    ctx.stroke();
  }

  function sampleIndex(frameIndex) {
    const payload = state.payload;
    if (!payloadIsDrawable(payload)) {
      return 0;
    }
    const sampleCount = Number(payload.sample_count || 0);
    return Math.max(0, Math.min(Number(frameIndex || 0), sampleCount - 1));
  }

  function drawMotion(frameIndex) {
    const target = contextFor("motion");
    const payload = state.payload;
    if (!target || !payloadIsDrawable(payload)) {
      clearPanel("motion", "No drawable motion payload.");
      return;
    }
    const { ctx, metrics } = target;
    const positions = payload.positions;
    const index = sampleIndex(frameIndex);
    state.frameIndex = index;

    ctx.clearRect(0, 0, metrics.width, metrics.height);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, metrics.width, metrics.height);
    drawMotionReference(ctx, payload, metrics);

    const pivot = motionProject(payload, 0, 0, metrics);
    const p1 = motionProject(payload, positions.x1[index], positions.y1[index], metrics);
    const p2 = motionProject(payload, positions.x2[index], positions.y2[index], metrics);

    ctx.strokeStyle = "rgba(68, 16, 173, 0.16)";
    ctx.lineWidth = 1 * metrics.ratio;
    ctx.beginPath();
    for (let i = 0; i <= index; i += Math.max(1, Math.floor(payload.sample_count / 400))) {
      const trail = motionProject(payload, positions.x2[i], positions.y2[i], metrics);
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
    ctx.moveTo(pivot.x, pivot.y);
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

    const time = payload.time && payload.time[index] !== undefined ? payload.time[index].toFixed(3) : "?";
    ctx.fillStyle = "#1d2433";
    ctx.font = `${13 * metrics.ratio}px Arial, sans-serif`;
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.fillText(`run ${payload.run_id} · frame ${index}/${payload.sample_count - 1} · t=${time}s`, 14 * metrics.ratio, 22 * metrics.ratio);
    ctx.fillText("physical x right; physical y up; screen y is a rendering transform", 14 * metrics.ratio, 42 * metrics.ratio);
    ctx.fillText("equal physical scale on x/y", 14 * metrics.ratio, 62 * metrics.ratio);
  }

  function drawTimeSeries(frameIndex) {
    const target = contextFor("timeSeries");
    const payload = state.payload;
    if (!target || !payloadIsDrawable(payload)) {
      clearPanel("timeSeries", "Run a successful simulation to inspect angular displacement.");
      return;
    }
    const { ctx, metrics } = target;
    const index = sampleIndex(frameIndex);
    const time = payload.time || [];
    const theta1 = payload.angular_state.theta1_deg || [];
    const theta2 = payload.angular_state.theta2_deg || [];
    const xBounds = arrayBounds(time, 0.02);
    const yBounds = arrayBounds([...theta1, ...theta2], 0.08);
    const area = plotArea(metrics);

    ctx.clearRect(0, 0, metrics.width, metrics.height);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, metrics.width, metrics.height);
    drawPlotReference(ctx, metrics, area, "time / seconds", "angle / degrees");

    function drawLine(values, color) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2 * metrics.ratio;
      ctx.beginPath();
      for (let i = 0; i < time.length; i++) {
        const point = plotProject(time[i], values[i], xBounds, yBounds, area);
        if (i === 0) {
          ctx.moveTo(point.x, point.y);
        } else {
          ctx.lineTo(point.x, point.y);
        }
      }
      ctx.stroke();
    }

    drawLine(theta1, "#F4762F");
    drawLine(theta2, "#4EC5AE");

    const selectedTime = Number(time[index] || 0);
    const cursor = plotProject(selectedTime, yBounds.min, xBounds, yBounds, area);
    ctx.strokeStyle = "#26364f";
    ctx.lineWidth = 1.2 * metrics.ratio;
    ctx.setLineDash([4 * metrics.ratio, 4 * metrics.ratio]);
    ctx.beginPath();
    ctx.moveTo(cursor.x, area.top);
    ctx.lineTo(cursor.x, area.bottom);
    ctx.stroke();
    ctx.setLineDash([]);

    const p1 = plotProject(selectedTime, theta1[index], xBounds, yBounds, area);
    const p2 = plotProject(selectedTime, theta2[index], xBounds, yBounds, area);
    ctx.fillStyle = "#9B1B30";
    ctx.beginPath();
    ctx.arc(p1.x, p1.y, 4.5 * metrics.ratio, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = "#006D77";
    ctx.beginPath();
    ctx.arc(p2.x, p2.y, 4.5 * metrics.ratio, 0, 2 * Math.PI);
    ctx.fill();

    ctx.fillStyle = "#1d2433";
    ctx.font = `${13 * metrics.ratio}px Arial, sans-serif`;
    ctx.textAlign = "left";
    ctx.fillText("Angular displacement time series", area.left, 18 * metrics.ratio);
    ctx.fillStyle = "#F4762F";
    ctx.fillText("theta1", area.right - 112 * metrics.ratio, 18 * metrics.ratio);
    ctx.fillStyle = "#4EC5AE";
    ctx.fillText("theta2", area.right - 58 * metrics.ratio, 18 * metrics.ratio);
  }

  function drawProjection(frameIndex) {
    const target = contextFor("projection");
    const payload = state.payload;
    if (!target || !payloadIsDrawable(payload)) {
      clearPanel("projection", "Run a successful simulation to inspect the angular state projection.");
      return;
    }
    const { ctx, metrics } = target;
    const index = sampleIndex(frameIndex);
    const theta1 = payload.angular_state.theta1_deg || [];
    const theta2 = payload.angular_state.theta2_deg || [];
    const xBounds = arrayBounds(theta1, 0.08);
    const yBounds = arrayBounds(theta2, 0.08);
    const area = plotArea(metrics);

    ctx.clearRect(0, 0, metrics.width, metrics.height);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, metrics.width, metrics.height);
    drawPlotReference(ctx, metrics, area, "theta1 / degrees", "theta2 / degrees");

    ctx.strokeStyle = "#4410AD";
    ctx.lineWidth = 2 * metrics.ratio;
    ctx.beginPath();
    for (let i = 0; i < theta1.length; i++) {
      const point = plotProject(theta1[i], theta2[i], xBounds, yBounds, area);
      if (i === 0) {
        ctx.moveTo(point.x, point.y);
      } else {
        ctx.lineTo(point.x, point.y);
      }
    }
    ctx.stroke();

    const marker = plotProject(theta1[index], theta2[index], xBounds, yBounds, area);
    ctx.fillStyle = "#F4762F";
    ctx.beginPath();
    ctx.arc(marker.x, marker.y, 6 * metrics.ratio, 0, 2 * Math.PI);
    ctx.fill();

    ctx.fillStyle = "#1d2433";
    ctx.font = `${13 * metrics.ratio}px Arial, sans-serif`;
    ctx.textAlign = "left";
    ctx.fillText("Theta-theta angular state projection", area.left, 18 * metrics.ratio);
  }

  function selectedReadout(frameIndex) {
    const payload = state.payload;
    if (!payloadIsDrawable(payload)) {
      return "No selected state.";
    }
    const index = sampleIndex(frameIndex);
    const selectedTime = Number(payload.time[index] || 0);
    const selectedTheta1 = Number(payload.angular_state.theta1_deg[index] || 0);
    const selectedTheta2 = Number(payload.angular_state.theta2_deg[index] || 0);
    return [
      `run ${payload.run_id}`,
      `frame ${index}/${payload.sample_count - 1}`,
      `t=${selectedTime.toFixed(4)}s`,
      `theta1=${selectedTheta1.toFixed(3)} deg`,
      `theta2=${selectedTheta2.toFixed(3)} deg`,
      "Motion, time series, and projection are Canvas-native views sharing one selected frame.",
    ].join("\n");
  }

  function drawAll(frameIndex) {
    if (!payloadIsDrawable(state.payload)) {
      return clearAll("No drawable motion payload.");
    }
    const index = sampleIndex(frameIndex);
    drawMotion(index);
    drawTimeSeries(index);
    drawProjection(index);
    state.lastStatus = `run ${state.payload.run_id}; frame ${index}/${state.payload.sample_count - 1}; playing=${state.playing}`;
    const readout = selectedReadout(index);
    const statusEl = document.getElementById("tier3c-canvas-status");
    const readoutEl = document.getElementById("tier3c-selected-readout");
    if (statusEl) {
      statusEl.innerText = state.lastStatus;
    }
    if (readoutEl) {
      readoutEl.innerText = readout;
    }
    return [state.lastStatus, readout];
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
      return clearAll("No motion payload.");
    }
    if (payload.kind === "clear") {
      cancelLoop();
      return clearAll(`run ${payload.run_id}: cleared`);
    }
    if (payload.kind === "failure") {
      cancelLoop();
      return clearAll(`run ${payload.run_id}: simulated failure`);
    }
    return drawAll(sameRun ? state.frameIndex : 0);
  }

  function play(payload) {
    if (payload && payload.run_id !== state.activeRunId) {
      setPayload(payload);
    }
    if (!payloadIsDrawable(state.payload)) {
      return clearAll("Cannot play without a successful motion payload.");
    }
    if (state.playing) {
      return [state.lastStatus, selectedReadout(state.frameIndex)];
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
        drawAll(state.frameIndex);
        cancelLoop();
        return;
      }
      drawAll(nextFrame);
      state.rafHandle = window.requestAnimationFrame(tick);
    }

    state.rafHandle = window.requestAnimationFrame(tick);
    state.lastStatus = `run ${runId}; playback started`;
    return [state.lastStatus, selectedReadout(state.frameIndex)];
  }

  function pause() {
    cancelLoop();
    drawAll(state.frameIndex);
    return [`run ${state.activeRunId}; paused at frame ${state.frameIndex}`, selectedReadout(state.frameIndex)];
  }

  function resetPlayback() {
    cancelLoop();
    state.frameIndex = 0;
    drawAll(0);
    return [`run ${state.activeRunId}; reset to frame 0`, selectedReadout(0)];
  }

  function scrub(frameIndex) {
    cancelLoop();
    drawAll(frameIndex);
    return [`run ${state.activeRunId}; scrubbed to frame ${state.frameIndex}`, selectedReadout(state.frameIndex)];
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

  window.tier3cCanvasManager = {
    handleCanvasEvent,
    state,
  };

  window.dash_clientside = Object.assign({}, window.dash_clientside, {
    tier3c_canvas: {
      handleCanvasEvent,
    },
  });
})();
