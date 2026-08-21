(function () {
  "use strict";

  const colours = {
    original: "#00635d",
    nearby: "#b7791f",
    ink: "#1f2933",
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

  function screenPoints(geometry, origin, scale) {
    const point = (x, y) => [origin.x + x * scale, origin.y - y * scale];
    return {
      pivot: [origin.x, origin.y],
      first: point(geometry.x1, geometry.y1),
      second: point(geometry.x2, geometry.y2),
    };
  }

  function insetSegment(start, end, startInset, endInset) {
    const dx = end[0] - start[0];
    const dy = end[1] - start[1];
    const length = Math.hypot(dx, dy);
    if (length <= startInset + endInset || length === 0) return null;
    const ux = dx / length;
    const uy = dy / length;
    return {
      start: [start[0] + ux * startInset, start[1] + uy * startInset],
      end: [end[0] - ux * endInset, end[1] - uy * endInset],
    };
  }

  function drawLinks(context, points, colour, options) {
    const firstRadius = 7;
    const secondRadius = 9;
    const capAllowance = options.lineWidth / 2;
    const firstLink = insetSegment(
      points.pivot,
      points.first,
      0,
      firstRadius + capAllowance
    );
    const secondLink = insetSegment(
      points.first,
      points.second,
      firstRadius + capAllowance,
      secondRadius + capAllowance
    );

    context.save();
    context.strokeStyle = colour;
    context.lineWidth = options.lineWidth;
    context.globalAlpha = options.alpha;
    context.lineCap = "round";
    if (options.dashed) context.setLineDash([7, 6]);
    [firstLink, secondLink].forEach((segment) => {
      if (!segment) return;
      context.beginPath();
      context.moveTo(segment.start[0], segment.start[1]);
      context.lineTo(segment.end[0], segment.end[1]);
      context.stroke();
    });
    context.setLineDash([]);
    context.restore();
  }

  function drawBobs(context, points, colour, options) {
    context.save();
    context.fillStyle = colour;
    context.globalAlpha = options.alpha;
    [points.first, points.second].forEach((position, index) => {
      context.beginPath();
      context.arc(position[0], position[1], index === 0 ? 7 : 9, 0, Math.PI * 2);
      context.fill();
      context.strokeStyle = "rgba(31, 41, 51, 0.28)";
      context.lineWidth = 1.5;
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
    context.strokeStyle = "rgba(63, 79, 79, 0.13)";
    context.lineWidth = 1;
    context.beginPath();
    context.arc(origin.x, origin.y, scale * 2, 0, Math.PI * 2);
    context.stroke();
    context.restore();

    const rendered = trajectories.map((item) => ({
      ...item,
      points: screenPoints(item.geometry, origin, scale),
    }));
    rendered.forEach((item) => {
      drawLinks(context, item.points, item.colour, item.options);
    });
    rendered.forEach((item) => {
      drawBobs(context, item.points, item.colour, item.options);
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
    const maximum = 2 * playback.payload.total_length_metres;
    const margin = { left: 76, right: 24, top: 20, bottom: 52 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const x = (time) => margin.left + (time / duration) * plotWidth;
    const y = (value) => margin.top + plotHeight - (value / maximum) * plotHeight;

    context.save();
    context.strokeStyle = colours.grid;
    context.fillStyle = colours.traceInk;
    context.font = '12px "Helvetica Neue", Helvetica, Arial, sans-serif';
    context.lineWidth = 1;
    [0, 0.25, 0.5, 0.75, 1].forEach((portion) => {
      const gridY = margin.top + plotHeight * portion;
      context.beginPath();
      context.moveTo(margin.left, gridY);
      context.lineTo(width - margin.right, gridY);
      context.stroke();
      context.textAlign = "right";
      context.fillText(
        `${(maximum * (1 - portion)).toFixed(1)}`,
        margin.left - 10,
        gridY + 4
      );
    });
    context.strokeStyle = colours.traceInk;
    context.beginPath();
    context.moveTo(margin.left, margin.top);
    context.lineTo(margin.left, margin.top + plotHeight);
    context.lineTo(width - margin.right, margin.top + plotHeight);
    context.stroke();

    [0, 0.5, 1].forEach((portion) => {
      const tickX = margin.left + plotWidth * portion;
      context.textAlign = portion === 0 ? "left" : portion === 1 ? "right" : "center";
      context.fillText(`${(duration * portion).toFixed(0)}`, tickX, height - 29);
    });
    context.textAlign = "center";
    context.fillText("time (s)", margin.left + plotWidth / 2, height - 8);
    context.save();
    context.translate(18, margin.top + plotHeight / 2);
    context.rotate(-Math.PI / 2);
    context.fillText("separation (m)", 0, 0);
    context.restore();

    context.strokeStyle = colours.original;
    context.lineWidth = 2.5;
    context.beginPath();
    values.slice(0, frame.index + 1).forEach((value, index) => {
      const pointX = x(index / playback.payload.output_rate_hz);
      const pointY = y(value);
      if (index === 0) context.moveTo(pointX, pointY);
      else context.lineTo(pointX, pointY);
    });
    context.lineTo(x(playback.elapsed), y(frame.separationMetres));
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
