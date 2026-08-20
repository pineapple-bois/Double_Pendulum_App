(function () {
  "use strict";

  const colours = {
    original: "#1bb3a9",
    nearby: "#ff9d5c",
    ink: "#edf7f5",
    traceInk: "#3f4f4f",
    grid: "rgba(31, 41, 51, 0.14)",
  };

  const playback = {
    payload: null,
    elapsed: 0,
    speed: 1,
    playing: false,
    lastTimestamp: null,
    animationFrame: null,
    bindingsReady: false,
    sequence: 0,
  };

  function element(id) {
    return document.getElementById(id);
  }

  function prepareCanvas(canvas) {
    if (!canvas) return null;
    const ratio = window.devicePixelRatio || 1;
    const width = Math.max(1, canvas.clientWidth);
    const height = Math.max(1, canvas.clientHeight);
    const pixelWidth = Math.round(width * ratio);
    const pixelHeight = Math.round(height * ratio);
    if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
      canvas.width = pixelWidth;
      canvas.height = pixelHeight;
    }
    const context = canvas.getContext("2d");
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, width, height);
    return { context, width, height };
  }

  function sampleAt(series, index, fraction) {
    const next = Math.min(index + 1, series.length - 1);
    return series[index] + (series[next] - series[index]) * fraction;
  }

  function frameAt(time) {
    const payload = playback.payload;
    const lastIndex = payload.time_s.length - 1;
    const exact = Math.min(time * payload.output_rate_hz, lastIndex);
    const index = Math.floor(exact);
    const fraction = exact - index;
    const trajectory = (name) => {
      const item = payload[name];
      return {
        x1: sampleAt(item.x1, index, fraction),
        y1: sampleAt(item.y1, index, fraction),
        x2: sampleAt(item.x2, index, fraction),
        y2: sampleAt(item.y2, index, fraction),
      };
    };
    return {
      index,
      fraction,
      original: trajectory("original"),
      nearby: trajectory("nearby"),
      separation: sampleAt(payload.separation_normalized, index, fraction),
      separationMetres: sampleAt(payload.separation_metres, index, fraction),
    };
  }

  function drawPendulum(context, geometry, origin, scale, colour, options) {
    const point = (x, y) => [origin.x + x * scale, origin.y - y * scale];
    const pivot = [origin.x, origin.y];
    const first = point(geometry.x1, geometry.y1);
    const second = point(geometry.x2, geometry.y2);

    context.save();
    context.strokeStyle = colour;
    context.fillStyle = colour;
    context.lineWidth = options.lineWidth;
    context.globalAlpha = options.alpha;
    context.lineCap = "round";
    if (options.dashed) context.setLineDash([7, 6]);
    context.beginPath();
    context.moveTo(pivot[0], pivot[1]);
    context.lineTo(first[0], first[1]);
    context.lineTo(second[0], second[1]);
    context.stroke();
    context.setLineDash([]);

    [first, second].forEach((position, index) => {
      context.beginPath();
      context.arc(position[0], position[1], index === 0 ? 7 : 9, 0, Math.PI * 2);
      context.fill();
      context.strokeStyle = "rgba(5, 20, 24, 0.76)";
      context.lineWidth = 2;
      context.stroke();
    });
    context.restore();
  }

  function drawPivot(context, origin) {
    context.save();
    context.fillStyle = colours.ink;
    context.beginPath();
    context.arc(origin.x, origin.y, 5, 0, Math.PI * 2);
    context.fill();
    context.restore();
  }

  function drawMotionCanvas(canvasId, trajectories) {
    const prepared = prepareCanvas(element(canvasId));
    if (!prepared) return;
    const { context, width, height } = prepared;
    const origin = { x: width / 2, y: height / 2 };
    const scale = Math.min(width, height) * 0.215;

    context.save();
    context.strokeStyle = "rgba(210, 236, 232, 0.10)";
    context.lineWidth = 1;
    context.beginPath();
    context.arc(origin.x, origin.y, scale * 2, 0, Math.PI * 2);
    context.stroke();
    context.restore();

    trajectories.forEach((item) => {
      drawPendulum(context, item.geometry, origin, scale, item.colour, item.options);
    });
    drawPivot(context, origin);
  }

  function drawTrace(frame) {
    const canvas = element("prototype-separation-canvas");
    const prepared = prepareCanvas(canvas);
    if (!prepared || !playback.payload) return;
    const { context, width, height } = prepared;
    const values = playback.payload.separation_metres;
    const duration = playback.payload.duration_seconds;
    const maximum = Math.max(playback.payload.max_separation_metres, 1e-9);
    const margin = { left: 60, right: 16, top: 18, bottom: 28 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const x = (time) => margin.left + (time / duration) * plotWidth;
    const y = (value) => margin.top + plotHeight - (value / maximum) * plotHeight;

    context.save();
    context.strokeStyle = colours.grid;
    context.fillStyle = colours.traceInk;
    context.font = "12px ui-monospace, SFMono-Regular, Menlo, monospace";
    context.lineWidth = 1;
    [0, 0.5, 1].forEach((portion) => {
      const gridY = margin.top + plotHeight * portion;
      context.beginPath();
      context.moveTo(margin.left, gridY);
      context.lineTo(width - margin.right, gridY);
      context.stroke();
    });
    context.fillText(`${maximum.toPrecision(3)} m`, 4, margin.top + 4);
    context.fillText("0", 28, margin.top + plotHeight + 4);
    context.fillText("0 s", margin.left, height - 6);
    context.textAlign = "right";
    context.fillText(`${duration.toFixed(0)} s`, width - margin.right, height - 6);
    context.textAlign = "left";

    context.strokeStyle = "#b8efe9";
    context.lineWidth = 2;
    context.beginPath();
    values.forEach((value, index) => {
      const pointX = x(index / playback.payload.output_rate_hz);
      const pointY = y(value);
      if (index === 0) context.moveTo(pointX, pointY);
      else context.lineTo(pointX, pointY);
    });
    context.stroke();

    const cursorX = x(playback.elapsed);
    context.strokeStyle = colours.nearby;
    context.lineWidth = 1.5;
    context.beginPath();
    context.moveTo(cursorX, margin.top);
    context.lineTo(cursorX, margin.top + plotHeight);
    context.stroke();
    context.fillStyle = colours.nearby;
    context.beginPath();
    context.arc(cursorX, y(frame.separationMetres), 4, 0, Math.PI * 2);
    context.fill();
    context.restore();
  }

  function render() {
    if (!playback.payload) return;
    const frame = frameAt(playback.elapsed);

    drawMotionCanvas("prototype-overlay-canvas", [
      {
        geometry: frame.original,
        colour: colours.original,
        options: { lineWidth: 6, alpha: 0.84, dashed: false },
      },
      {
        geometry: frame.nearby,
        colour: colours.nearby,
        options: { lineWidth: 3.5, alpha: 0.94, dashed: true },
      },
    ]);
    drawMotionCanvas("prototype-original-canvas", [
      {
        geometry: frame.original,
        colour: colours.original,
        options: { lineWidth: 5, alpha: 1, dashed: false },
      },
    ]);
    drawMotionCanvas("prototype-nearby-canvas", [
      {
        geometry: frame.nearby,
        colour: colours.nearby,
        options: { lineWidth: 5, alpha: 1, dashed: false },
      },
    ]);

    element("prototype-time").textContent = `${playback.elapsed.toFixed(2)} s`;
    element("prototype-current-separation").textContent = `${frame.separationMetres.toFixed(4)} m`;
    drawTrace(frame);
  }

  function setPlaying(playing) {
    playback.playing = playing;
    playback.lastTimestamp = null;
    const button = element("prototype-pause");
    if (button) button.textContent = playing ? "Pause" : "Resume";
  }

  function tick(timestamp) {
    if (playback.payload && playback.playing) {
      if (playback.lastTimestamp === null) playback.lastTimestamp = timestamp;
      const delta = Math.min((timestamp - playback.lastTimestamp) / 1000, 0.1);
      playback.lastTimestamp = timestamp;
      playback.elapsed = Math.min(
        playback.payload.duration_seconds,
        playback.elapsed + delta * playback.speed
      );
      render();
      if (playback.elapsed >= playback.payload.duration_seconds) {
        setPlaying(false);
      }
    }
    playback.animationFrame = window.requestAnimationFrame(tick);
  }

  function validPayload(payload) {
    return Boolean(
      payload &&
        payload.status === "success" &&
        payload.rendering &&
        payload.rendering.drawable &&
        Array.isArray(payload.time_s) &&
        payload.time_s.length > 1 &&
        payload.original &&
        payload.nearby &&
        payload.original.x2.length === payload.time_s.length &&
        payload.nearby.x2.length === payload.time_s.length &&
        payload.separation_normalized.length === payload.time_s.length
    );
  }

  function showEmpty(message, failed) {
    const empty = element("prototype-empty-stage");
    if (empty) {
      empty.classList.add("is-visible");
      empty.classList.toggle("is-failed", Boolean(failed));
      const paragraph = empty.querySelector("p");
      if (paragraph) paragraph.textContent = message;
    }
  }

  function clearRelationshipReadout() {
    const time = element("prototype-time");
    const current = element("prototype-current-separation");
    if (time) time.textContent = "0.00 s";
    if (current) current.textContent = "—";
    prepareCanvas(element("prototype-separation-canvas"));
  }

  function hideEmpty() {
    const empty = element("prototype-empty-stage");
    if (empty) empty.classList.remove("is-visible", "is-failed");
  }

  function ensureBindings() {
    if (playback.bindingsReady || !element("prototype-pause")) return;
    playback.bindingsReady = true;
    element("prototype-pause").addEventListener("click", () => {
      if (!playback.payload) return;
      setPlaying(!playback.playing);
    });
    element("prototype-reset").addEventListener("click", () => {
      if (!playback.payload) return;
      playback.elapsed = 0;
      setPlaying(false);
      render();
    });
    element("prototype-replay").addEventListener("click", () => {
      if (!playback.payload) return;
      playback.elapsed = 0;
      setPlaying(true);
      render();
    });
    window.addEventListener("resize", () => {
      if (playback.payload) render();
    });
  }

  function startBindingPoll() {
    ensureBindings();
    if (!playback.bindingsReady) window.setTimeout(startBindingPoll, 50);
  }

  window.dash_clientside = Object.assign({}, window.dash_clientside, {
    sensitivityPrototype: {
      applyPayload: function (payload) {
        ensureBindings();
        playback.sequence += 1;
        if (!payload) return { sequence: playback.sequence, status: "empty" };
        if (!validPayload(payload)) {
          playback.payload = null;
          playback.elapsed = 0;
          setPlaying(false);
          showEmpty(payload.message || "This run cannot be animated.", true);
          clearRelationshipReadout();
          return { sequence: playback.sequence, status: "failed" };
        }
        playback.payload = payload;
        playback.elapsed = 0;
        hideEmpty();
        setPlaying(Boolean(payload.rendering.autoplay_allowed));
        render();
        return { sequence: playback.sequence, status: "ready" };
      },

      setMode: function (mode) {
        const stage = element("prototype-animation-stage");
        if (stage) {
          stage.classList.toggle("mode-superimposed", mode === "superimposed");
          stage.classList.toggle("mode-side-by-side", mode === "side_by_side");
        }
        window.requestAnimationFrame(() => {
          if (playback.payload) render();
        });
        return { mode: mode, timestamp: Date.now() };
      },

      setSpeed: function (speed) {
        const parsed = Number.parseFloat(speed);
        playback.speed = Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
        return { speed: playback.speed, timestamp: Date.now() };
      },

      markInputsChanged: function () {
        if (playback.payload) {
          setPlaying(false);
        }
        return { timestamp: Date.now() };
      },
    },
  });

  startBindingPoll();
  if (!playback.animationFrame) playback.animationFrame = window.requestAnimationFrame(tick);
})();
