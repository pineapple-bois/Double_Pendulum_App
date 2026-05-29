(function () {
    "use strict";

    const SCHEMA_VERSION = "canvas_motion_payload.v1";
    const STATUS = {
        SUCCESS: "success",
        STALE: "stale",
        FAILED: "failed",
        CLEARED: "cleared",
        EMPTY: "empty",
        RUNNING: "running",
    };
    const IDS = {
        shell: "simulation-interaction-shell",
        workspace: "canvas-inspection-workspace",
        motionCanvas: "canvas-motion-view",
        timeCanvas: "canvas-time-series-view",
        projectionCanvas: "canvas-projection-view",
        readout: "selected-state-readout",
        play: "simulation-play-button",
        pause: "simulation-pause-button",
        reset: "simulation-reset-button",
        scrubber: "simulation-scrubber",
        options: "simulation-display-options",
        frameIndicator: "simulation-frame-indicator",
        submit: "submit-val",
    };
    const REQUEST_INPUT_IDS = [
        "model-type",
        "system-type",
        "param_g",
        "param_l1",
        "param_l2",
        "param_m1",
        "param_m2",
        "param_M1",
        "param_M2",
        "init_cond_theta1",
        "init_cond_theta2",
        "init_cond_omega1",
        "init_cond_omega2",
        "time_start",
        "time_end",
        "unity-parameters",
    ];
    const REQUIRED_ARRAYS = [
        "time_s",
        "theta1_deg",
        "theta2_deg",
        "x1",
        "y1",
        "x2",
        "y2",
    ];
    const PLOTLY_FRAME_DURATION_MS = 33;
    const PLOTLY_FRAME_SAMPLE_STEP = 10;
    const PALETTE = {
        ink: "#0d295a",
        navy: "#041843",
        slate: "#496284",
        muted: "#73859c",
        blue: "#244a7d",
        blueSoft: "#5f83a5",
        teal: "#2f7d7b",
        tealSoft: "#76aaa7",
        grid: "rgba(183, 197, 214, 0.38)",
        gridFine: "rgba(183, 197, 214, 0.22)",
        axis: "rgba(13, 41, 90, 0.72)",
        trace: "rgba(47, 125, 123, 0.28)",
        traceSoft: "rgba(95, 131, 165, 0.18)",
        marker: "#2f7d5c",
        staleFill: "rgba(184, 135, 46, 0.12)",
        staleText: "#6f4a12",
        white: "#ffffff",
    };

    const rendererState = {
        shell: null,
        canvases: {},
        controls: {},
        payload: null,
        resultState: null,
        activeRunId: null,
        minimumRunId: 0,
        activePayloadKey: null,
        resultStatus: STATUS.EMPTY,
        selectedFrame: 0,
        playbackState: "idle",
        playing: false,
        rafId: null,
        loopToken: 0,
        playbackStartTimestamp: null,
        playbackStartFrame: 0,
        resizeRaf: null,
        metrics: null,
        options: {
            axes: true,
            grid: true,
        },
        boundShell: null,
        resizeBound: false,
        globalEventsBound: false,
        observer: null,
    };

    function byId(id) {
        return document.getElementById(id);
    }

    function hasShell() {
        return Boolean(byId(IDS.shell));
    }

    function init() {
        const shell = byId(IDS.shell);
        if (!shell) {
            cancelPlayback("cancelled");
            return false;
        }

        rendererState.shell = shell;
        rendererState.canvases = {
            motion: byId(IDS.motionCanvas),
            time: byId(IDS.timeCanvas),
            projection: byId(IDS.projectionCanvas),
        };
        rendererState.controls = {
            play: byId(IDS.play),
            pause: byId(IDS.pause),
            reset: byId(IDS.reset),
            scrubber: byId(IDS.scrubber),
            options: byId(IDS.options),
            frameIndicator: byId(IDS.frameIndicator),
            readout: byId(IDS.readout),
            workspace: byId(IDS.workspace),
        };

        if (!rendererState.canvases.motion || !rendererState.canvases.time || !rendererState.canvases.projection) {
            return false;
        }

        if (rendererState.boundShell !== shell) {
            bindControls();
            rendererState.boundShell = shell;
        }

        if (!rendererState.resizeBound) {
            window.addEventListener("resize", scheduleResize);
            rendererState.resizeBound = true;
        }
        if (!rendererState.globalEventsBound) {
            bindGlobalEvents();
            rendererState.globalEventsBound = true;
        }

        return true;
    }

    function bindGlobalEvents() {
        document.addEventListener("click", function (event) {
            if (targetWithinId(event.target, IDS.submit)) {
                handleRunRequested();
                return;
            }
            if (targetWithinAnyId(event.target, REQUEST_INPUT_IDS)) {
                markCurrentPayloadStale("Settings changed - rerun to update.");
            }
        }, true);
        document.addEventListener("input", function (event) {
            if (targetWithinAnyId(event.target, REQUEST_INPUT_IDS)) {
                markCurrentPayloadStale("Settings changed - rerun to update.");
            }
        }, true);
        document.addEventListener("change", function (event) {
            if (targetWithinAnyId(event.target, REQUEST_INPUT_IDS)) {
                markCurrentPayloadStale("Settings changed - rerun to update.");
            }
        }, true);
    }

    function targetWithinAnyId(target, ids) {
        return ids.some(function (id) {
            return targetWithinId(target, id);
        });
    }

    function targetWithinId(target, id) {
        let node = target;
        while (node && node !== document) {
            if (node.id === id) {
                return true;
            }
            node = node.parentElement;
        }
        return false;
    }

    function handleRunRequested() {
        if (!hasShell()) {
            return;
        }
        rendererState.minimumRunId = Math.max(
            rendererState.minimumRunId,
            Number(rendererState.activeRunId || 0) + 1
        );
        rendererState.activeRunId = rendererState.minimumRunId;
        rendererState.payload = null;
        rendererState.metrics = null;
        rendererState.activePayloadKey = null;
        rendererState.resultStatus = STATUS.RUNNING;
        rendererState.selectedFrame = 0;
        cancelPlayback("cancelled");
        renderNonDrawable(STATUS.RUNNING, "Preparing simulation output.");
    }

    function markCurrentPayloadStale(message) {
        if (!hasShell() || rendererState.resultStatus !== STATUS.SUCCESS || !rendererState.payload) {
            return;
        }
        rendererState.resultStatus = STATUS.STALE;
        cancelPlayback("cancelled");
        setShellStatus(STATUS.STALE);
        if (canInspect()) {
            drawAll();
            updateReadout((message || "Settings changed - rerun to update.") + " " + currentFrameSummary());
        } else {
            renderNonDrawable(STATUS.STALE, message || "Settings changed - rerun to update.");
        }
        updateControls();
    }

    function bindControls() {
        const controls = rendererState.controls;
        if (controls.play) {
            controls.play.addEventListener("click", play);
        }
        if (controls.pause) {
            controls.pause.addEventListener("click", pause);
        }
        if (controls.reset) {
            controls.reset.addEventListener("click", reset);
        }
        if (controls.scrubber) {
            controls.scrubber.addEventListener("input", function (event) {
                scrub(Number(event.target.value));
            });
            controls.scrubber.addEventListener("change", function (event) {
                scrub(Number(event.target.value));
            });
        }
        if (controls.options) {
            controls.options.addEventListener("change", function (event) {
                const option = optionNameFromInput(event.target);
                if (!option) {
                    return;
                }
                setOptions(Object.assign({}, rendererState.options, {
                    [option]: Boolean(event.target.checked),
                }));
            });
        }
        readOptionsFromDom();
    }

    function applyState(payload, resultState, playbackState) {
        try {
            if (!init()) {
                return;
            }

            const nextStatus = authoritativeStatus(payload, resultState);
            const previousRunId = rendererState.activeRunId;
            const previousPayloadKey = rendererState.activePayloadKey;
            rendererState.resultState = resultState || {};
            rendererState.resultStatus = nextStatus;
            setShellStatus(nextStatus);

            if (nextStatus === STATUS.RUNNING) {
                cancelPlayback("cancelled");
                rendererState.payload = null;
                rendererState.metrics = null;
                rendererState.activePayloadKey = null;
                rendererState.activeRunId = runIdFrom(resultState);
                rendererState.selectedFrame = 0;
                renderNonDrawable(STATUS.RUNNING, "Preparing simulation output.");
                return;
            }

            if (!payload || typeof payload !== "object") {
                cancelPlayback("cancelled");
                rendererState.payload = null;
                rendererState.metrics = null;
                rendererState.selectedFrame = 0;
                renderNonDrawable(nextStatus || STATUS.EMPTY, "No Canvas payload is available.");
                return;
            }

            if (payload.schema_version !== SCHEMA_VERSION) {
                cancelPlayback("cancelled");
                rendererState.payload = null;
                rendererState.metrics = null;
                rendererState.selectedFrame = 0;
                renderNonDrawable("unsupported", "Unsupported Canvas payload.");
                return;
            }

            if (nextStatus !== STATUS.SUCCESS && nextStatus !== STATUS.STALE) {
                const nextRunId = runIdFrom(payload);
                if (nextRunId > 0 && nextRunId < rendererState.minimumRunId) {
                    return;
                }
                rendererState.minimumRunId = Math.max(rendererState.minimumRunId, nextRunId);
                cancelPlayback("cancelled");
                rendererState.payload = null;
                rendererState.metrics = null;
                rendererState.activePayloadKey = payloadKey(payload, nextStatus);
                rendererState.activeRunId = runIdFrom(payload);
                rendererState.selectedFrame = 0;
                renderNonDrawable(nextStatus, payload.message || resultMessage(resultState, nextStatus));
                return;
            }

            const problems = drawableProblems(payload);
            if (problems.length > 0) {
                cancelPlayback("cancelled");
                rendererState.payload = null;
                rendererState.metrics = null;
                rendererState.selectedFrame = 0;
                renderNonDrawable("invalid", "Canvas payload could not be drawn.");
                return;
            }

            const nextRunId = runIdFrom(payload);
            const nextKey = payloadKey(payload, nextStatus);
            if (nextRunId > 0 && nextRunId < rendererState.minimumRunId) {
                return;
            }
            rendererState.minimumRunId = Math.max(rendererState.minimumRunId, nextRunId);

            if (nextStatus === STATUS.STALE) {
                cancelPlayback("cancelled");
            } else if (nextKey !== previousPayloadKey || nextRunId !== previousRunId) {
                cancelPlayback("idle");
            }

            rendererState.payload = payload;
            rendererState.metrics = buildMetrics(payload);
            rendererState.activeRunId = nextRunId;
            rendererState.activePayloadKey = nextKey;

            const sameRunStalePayload = previousRunId === nextRunId && nextStatus === STATUS.STALE;
            if (nextRunId !== previousRunId || (nextStatus === STATUS.SUCCESS && nextKey !== previousPayloadKey)) {
                rendererState.selectedFrame = 0;
            } else if (!sameRunStalePayload && playbackState && typeof playbackState.selected_frame === "number") {
                rendererState.selectedFrame = clampFrame(playbackState.selected_frame);
            } else {
                rendererState.selectedFrame = clampFrame(rendererState.selectedFrame);
            }

            drawAll();
            updateControls();
        } catch (error) {
            console.error("Simulation Canvas renderer error:", error);
            cancelPlayback("cancelled");
            renderNonDrawable(STATUS.FAILED, "Canvas renderer could not display the payload.");
        }
    }

    function authoritativeStatus(payload, resultState) {
        if (resultState && resultState.status) {
            return resultState.status;
        }
        if (payload && payload.status) {
            return payload.status;
        }
        return STATUS.EMPTY;
    }

    function resultMessage(resultState, status) {
        if (resultState && resultState.message) {
            return resultState.message;
        }
        if (status === STATUS.EMPTY) {
            return "No simulation run yet.";
        }
        if (status === STATUS.CLEARED) {
            return "Output cleared.";
        }
        if (status === STATUS.FAILED) {
            return "Simulation output failed.";
        }
        return "No drawable output is active.";
    }

    function runIdFrom(value) {
        const runId = value && value.run_id;
        return Number.isFinite(Number(runId)) ? Number(runId) : 0;
    }

    function payloadKey(payload, status) {
        return [
            runIdFrom(payload),
            status || payload.status || "",
            payload.payload_size_bytes || 0,
            payload.sample_count || 0,
        ].join(":");
    }

    function drawableProblems(payload) {
        const problems = [];
        const sampleCount = Number(payload.sample_count);
        if (!Number.isInteger(sampleCount) || sampleCount <= 0) {
            problems.push("sample_count");
            return problems;
        }
        if (!payload.rendering || payload.rendering.drawable !== true) {
            problems.push("rendering.drawable");
        }
        REQUIRED_ARRAYS.forEach(function (field) {
            if (!finiteArray(payload[field], sampleCount)) {
                problems.push(field);
            }
        });
        if (!strictlyIncreasing(payload.time_s)) {
            problems.push("time_s");
        }
        return problems;
    }

    function finiteArray(values, expectedLength) {
        if (!Array.isArray(values) || values.length !== expectedLength) {
            return false;
        }
        for (let index = 0; index < values.length; index += 1) {
            if (!Number.isFinite(Number(values[index]))) {
                return false;
            }
        }
        return true;
    }

    function strictlyIncreasing(values) {
        if (!Array.isArray(values) || values.length < 2) {
            return true;
        }
        for (let index = 1; index < values.length; index += 1) {
            if (Number(values[index]) <= Number(values[index - 1])) {
                return false;
            }
        }
        return true;
    }

    function buildMetrics(payload) {
        const projectionRanges = equalizeRanges(
            rangeForArrays([payload.theta1_deg], 0.08, 10),
            rangeForArrays([payload.theta2_deg], 0.08, 10),
            10
        );
        return {
            sampleCount: Number(payload.sample_count),
            timeRange: rangeForArrays([payload.time_s], 0.02, 1),
            angleRange: rangeForArrays([payload.theta1_deg, payload.theta2_deg], 0.08, 10),
            projectionXRange: projectionRanges.x,
            projectionYRange: projectionRanges.y,
            positionRange: buildPositionRange(payload),
        };
    }

    function rangeForArrays(arrays, paddingRatio, minimumSpan) {
        let minValue = Infinity;
        let maxValue = -Infinity;
        arrays.forEach(function (values) {
            values.forEach(function (rawValue) {
                const value = Number(rawValue);
                if (value < minValue) {
                    minValue = value;
                }
                if (value > maxValue) {
                    maxValue = value;
                }
            });
        });
        if (!Number.isFinite(minValue) || !Number.isFinite(maxValue)) {
            minValue = 0;
            maxValue = minimumSpan;
        }
        let span = maxValue - minValue;
        if (span < minimumSpan) {
            const midpoint = (minValue + maxValue) / 2;
            span = minimumSpan;
            minValue = midpoint - span / 2;
            maxValue = midpoint + span / 2;
        }
        const padding = span * paddingRatio;
        return {
            min: minValue - padding,
            max: maxValue + padding,
        };
    }

    function equalizeRanges(xRange, yRange, minimumSpan) {
        const xSpan = Math.max(minimumSpan || 1, xRange.max - xRange.min);
        const ySpan = Math.max(minimumSpan || 1, yRange.max - yRange.min);
        const span = Math.max(xSpan, ySpan);
        const xMid = (xRange.min + xRange.max) / 2;
        const yMid = (yRange.min + yRange.max) / 2;
        return {
            x: {
                min: xMid - span / 2,
                max: xMid + span / 2,
            },
            y: {
                min: yMid - span / 2,
                max: yMid + span / 2,
            },
        };
    }

    function buildPositionRange(payload) {
        const bounds = payload.bounds || {};
        const parameterValues = payload.parameters && payload.parameters.values ? payload.parameters.values : {};
        const lengthExtent = Math.abs(Number(parameterValues.l1) || 0) + Math.abs(Number(parameterValues.l2) || 0);
        const minX = Math.min(Number(bounds.min_x), 0);
        const maxX = Math.max(Number(bounds.max_x), 0);
        const minY = Math.min(Number(bounds.min_y), 0);
        const maxY = Math.max(Number(bounds.max_y), 0);
        const extent = Math.max(
            Math.abs(Number.isFinite(minX) ? minX : 0),
            Math.abs(Number.isFinite(maxX) ? maxX : 0),
            Math.abs(Number.isFinite(minY) ? minY : 0),
            Math.abs(Number.isFinite(maxY) ? maxY : 0),
            Number(bounds.max_abs_extent) || 0,
            lengthExtent,
            1
        ) * 1.12;
        return {
            min: -extent,
            max: extent,
            extent: extent,
        };
    }

    function play() {
        if (!canPlay()) {
            updateReadout("Run a current successful simulation before playing.");
            updateControls();
            return;
        }
        if (rendererState.playing) {
            return;
        }
        if (rendererState.selectedFrame >= rendererState.metrics.sampleCount - 1) {
            rendererState.selectedFrame = 0;
        }

        rendererState.playing = true;
        rendererState.playbackState = "playing";
        rendererState.loopToken += 1;
        rendererState.playbackStartTimestamp = null;
        rendererState.playbackStartFrame = rendererState.selectedFrame;
        const token = rendererState.loopToken;
        const runId = rendererState.activeRunId;
        updateControls();

        function step(timestamp) {
            if (!loopIsCurrent(token, runId)) {
                return;
            }
            if (rendererState.playbackStartTimestamp === null) {
                rendererState.playbackStartTimestamp = timestamp;
            }
            const elapsedSeconds = ((timestamp - rendererState.playbackStartTimestamp) / 1000) * plotlyBaselineRate();
            const targetTime = timeForFrame(rendererState.playbackStartFrame) + elapsedSeconds;
            rendererState.selectedFrame = frameForTime(targetTime);
            drawAll();
            if (rendererState.selectedFrame >= rendererState.metrics.sampleCount - 1) {
                rendererState.playing = false;
                rendererState.playbackState = "ended";
                rendererState.rafId = null;
                rendererState.playbackStartTimestamp = null;
                updateControls();
                return;
            }
            rendererState.rafId = window.requestAnimationFrame(step);
        }

        rendererState.rafId = window.requestAnimationFrame(step);
    }

    function plotlyBaselineRate() {
        const payload = rendererState.payload;
        const sampleCount = rendererState.metrics ? rendererState.metrics.sampleCount : 0;
        if (!payload || !Array.isArray(payload.time_s) || sampleCount < 2) {
            return 1;
        }
        const stepFrame = Math.min(PLOTLY_FRAME_SAMPLE_STEP, sampleCount - 1);
        const elapsedSimulationSeconds = Number(payload.time_s[stepFrame]) - Number(payload.time_s[0]);
        if (!Number.isFinite(elapsedSimulationSeconds) || elapsedSimulationSeconds <= 0) {
            return 1;
        }
        return elapsedSimulationSeconds / (PLOTLY_FRAME_DURATION_MS / 1000);
    }

    function timeForFrame(frameIndex) {
        if (!rendererState.payload || !Array.isArray(rendererState.payload.time_s)) {
            return 0;
        }
        return Number(rendererState.payload.time_s[clampFrame(frameIndex)]) || 0;
    }

    function frameForTime(targetTime) {
        const payload = rendererState.payload;
        if (!payload || !Array.isArray(payload.time_s) || payload.time_s.length === 0) {
            return 0;
        }
        const values = payload.time_s;
        const lastFrame = values.length - 1;
        if (Number(targetTime) <= Number(values[0])) {
            return 0;
        }
        if (Number(targetTime) >= Number(values[lastFrame])) {
            return lastFrame;
        }
        let low = 0;
        let high = lastFrame;
        while (low < high) {
            const midpoint = Math.floor((low + high) / 2);
            if (Number(values[midpoint]) < Number(targetTime)) {
                low = midpoint + 1;
            } else {
                high = midpoint;
            }
        }
        const previous = Math.max(0, low - 1);
        const previousDistance = Math.abs(Number(targetTime) - Number(values[previous]));
        const nextDistance = Math.abs(Number(values[low]) - Number(targetTime));
        return previousDistance <= nextDistance ? previous : low;
    }

    function loopIsCurrent(token, runId) {
        return (
            rendererState.playing &&
            rendererState.loopToken === token &&
            rendererState.activeRunId === runId &&
            rendererState.resultStatus === STATUS.SUCCESS &&
            rendererState.payload &&
            rendererState.payload.status === STATUS.SUCCESS
        );
    }

    function pause() {
        if (!rendererState.playing) {
            updateControls();
            return;
        }
        cancelPlayback("paused");
        drawAll();
        updateControls();
    }

    function reset() {
        if (!canInspect()) {
            cancelPlayback("cancelled");
            rendererState.selectedFrame = 0;
            renderNonDrawable(rendererState.resultStatus, "No inspectable Canvas payload is active.");
            return;
        }
        cancelPlayback("idle");
        rendererState.selectedFrame = 0;
        drawAll();
        updateControls();
    }

    function scrub(frameIndex) {
        if (!canInspect()) {
            cancelPlayback("cancelled");
            rendererState.selectedFrame = 0;
            renderNonDrawable(rendererState.resultStatus, "No inspectable Canvas payload is active.");
            return;
        }
        cancelPlayback("scrubbing");
        rendererState.selectedFrame = clampFrame(frameIndex);
        drawAll();
        updateControls();
    }

    function setOptions(options) {
        rendererState.options = {
            axes: Boolean(options.axes),
            grid: Boolean(options.grid),
        };
        syncOptionsToDom();
        if (canInspect()) {
            drawAll();
        } else {
            renderNonDrawable(rendererState.resultStatus, resultMessage(rendererState.resultState, rendererState.resultStatus));
        }
        updateControls();
    }

    function cancelPlayback(nextState) {
        if (rendererState.rafId !== null) {
            window.cancelAnimationFrame(rendererState.rafId);
            rendererState.rafId = null;
        }
        rendererState.loopToken += 1;
        rendererState.playing = false;
        rendererState.playbackState = nextState || "cancelled";
        rendererState.playbackStartTimestamp = null;
        rendererState.playbackStartFrame = rendererState.selectedFrame;
    }

    function canInspect() {
        return (
            rendererState.payload &&
            rendererState.metrics &&
            (rendererState.resultStatus === STATUS.SUCCESS || rendererState.resultStatus === STATUS.STALE)
        );
    }

    function canPlay() {
        return (
            canInspect() &&
            rendererState.resultStatus === STATUS.SUCCESS &&
            rendererState.payload.status === STATUS.SUCCESS &&
            rendererState.payload.rendering &&
            rendererState.payload.rendering.autoplay_allowed === true
        );
    }

    function clampFrame(frameIndex) {
        const sampleCount = rendererState.metrics ? rendererState.metrics.sampleCount : 1;
        const lastFrame = Math.max(0, sampleCount - 1);
        const numericFrame = Number.isFinite(Number(frameIndex)) ? Number(frameIndex) : 0;
        return Math.max(0, Math.min(lastFrame, Math.round(numericFrame)));
    }

    function drawAll() {
        if (!hasShell()) {
            cancelPlayback("cancelled");
            return;
        }
        if (!canInspect()) {
            renderNonDrawable(rendererState.resultStatus, resultMessage(rendererState.resultState, rendererState.resultStatus));
            return;
        }
        rendererState.selectedFrame = clampFrame(rendererState.selectedFrame);
        drawMotion();
        drawTimeSeries();
        drawProjection();
        updateReadoutForFrame();
        updateScrubber();
        updateControls();
    }

    function drawMotion() {
        const panel = canvasContext(rendererState.canvases.motion);
        if (!panel) {
            return;
        }
        const ctx = panel.ctx;
        const width = panel.width;
        const height = panel.height;
        const payload = rendererState.payload;
        const frame = rendererState.selectedFrame;
        const plot = squarePlotArea(width, height, { left: 38, right: 20, top: 18, bottom: 42 });
        const range = rendererState.metrics.positionRange;
        const map = motionMapper(plot, range);
        const p0 = map(0, 0);
        const p1 = map(Number(payload.x1[frame]), Number(payload.y1[frame]));
        const p2 = map(Number(payload.x2[frame]), Number(payload.y2[frame]));

        clearCanvas(ctx, width, height);
        drawPanelBackground(ctx, width, height);
        if (rendererState.options.grid) {
            drawMotionGrid(ctx, plot, range, map);
        }
        if (rendererState.options.axes) {
            drawMotionAxes(ctx, plot, range, map);
        }
        drawMotionTrace(ctx, payload, map, frame);

        ctx.lineCap = "round";
        ctx.lineWidth = 2.4;
        ctx.strokeStyle = PALETTE.ink;
        ctx.beginPath();
        ctx.moveTo(p0.x, p0.y);
        ctx.lineTo(p1.x, p1.y);
        ctx.stroke();

        ctx.strokeStyle = PALETTE.slate;
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();

        drawBob(ctx, p0.x, p0.y, 3.5, PALETTE.slate, PALETTE.white);
        drawBob(ctx, p1.x, p1.y, 5.5, PALETTE.blueSoft, PALETTE.ink);
        drawBob(ctx, p2.x, p2.y, 6.25, PALETTE.teal, PALETTE.ink);
        drawStaleOverlay(ctx, width, height);
    }

    function drawTimeSeries() {
        const panel = canvasContext(rendererState.canvases.time);
        if (!panel) {
            return;
        }
        const ctx = panel.ctx;
        const width = panel.width;
        const height = panel.height;
        const payload = rendererState.payload;
        const metrics = rendererState.metrics;
        const frame = rendererState.selectedFrame;
        const margin = { left: 48, right: 18, top: 30, bottom: 36 };
        const plot = plotArea(width, height, margin);
        const mapX = scaleLinear(metrics.timeRange, { min: plot.left, max: plot.right });
        const mapY = scaleLinear(metrics.angleRange, { min: plot.bottom, max: plot.top });

        clearCanvas(ctx, width, height);
        drawPanelBackground(ctx, width, height);
        drawPlotScaffold(ctx, plot, "time (s)", "angle (deg)");
        if (rendererState.options.grid) {
            drawPlotGrid(ctx, plot, 5, 4);
        }
        if (rendererState.options.axes) {
            drawPlotAxes(ctx, plot);
        }
        drawLineSeries(ctx, payload.time_s, payload.theta1_deg, mapX, mapY, PALETTE.blue);
        drawLineSeries(ctx, payload.time_s, payload.theta2_deg, mapX, mapY, PALETTE.teal);

        const cursorX = mapX(Number(payload.time_s[frame]));
        drawCursor(ctx, cursorX, plot.top, plot.bottom);
        drawBob(ctx, cursorX, mapY(Number(payload.theta1_deg[frame])), 4.25, PALETTE.blue, PALETTE.white);
        drawBob(ctx, cursorX, mapY(Number(payload.theta2_deg[frame])), 4.25, PALETTE.teal, PALETTE.white);
        drawLegend(ctx, plot.left, 18, [
            ["θ₁", PALETTE.blue],
            ["θ₂", PALETTE.teal],
        ]);
        drawStaleOverlay(ctx, width, height);
    }

    function drawProjection() {
        const panel = canvasContext(rendererState.canvases.projection);
        if (!panel) {
            return;
        }
        const ctx = panel.ctx;
        const width = panel.width;
        const height = panel.height;
        const payload = rendererState.payload;
        const metrics = rendererState.metrics;
        const frame = rendererState.selectedFrame;
        const plot = squarePlotArea(width, height, { left: 56, right: 18, top: 14, bottom: 54 });
        const mapX = scaleLinear(metrics.projectionXRange, { min: plot.left, max: plot.right });
        const mapY = scaleLinear(metrics.projectionYRange, { min: plot.bottom, max: plot.top });

        clearCanvas(ctx, width, height);
        drawPanelBackground(ctx, width, height);
        drawPlotScaffold(ctx, plot, "θ₁ (deg)", "θ₂ (deg)", { xOffset: 42, yOffset: 42 });
        if (rendererState.options.grid) {
            drawPlotGrid(ctx, plot, 5, 5);
        }
        if (rendererState.options.axes) {
            drawPlotAxes(ctx, plot);
            drawZeroAxes(ctx, plot, metrics.projectionXRange, metrics.projectionYRange, mapX, mapY);
            drawPlotTickLabels(ctx, plot, metrics.projectionXRange, metrics.projectionYRange, mapX, mapY);
        }

        ctx.save();
        ctx.strokeStyle = "rgba(36, 74, 125, 0.72)";
        ctx.lineWidth = 1.8;
        ctx.beginPath();
        for (let index = 0; index < payload.theta1_deg.length; index += 1) {
            const x = mapX(Number(payload.theta1_deg[index]));
            const y = mapY(Number(payload.theta2_deg[index]));
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }
        ctx.stroke();
        ctx.restore();

        drawBob(
            ctx,
            mapX(Number(payload.theta1_deg[frame])),
            mapY(Number(payload.theta2_deg[frame])),
            5.25,
            PALETTE.marker,
            PALETTE.white
        );
        drawStaleOverlay(ctx, width, height);
    }

    function renderNonDrawable(status, message) {
        if (!init()) {
            return;
        }
        setShellStatus(status || STATUS.EMPTY);
        const title = titleForStatus(status);
        const body = message || resultMessage(rendererState.resultState, status);
        drawMessage(rendererState.canvases.motion, title, body);
        drawMessage(rendererState.canvases.time, "Angular displacement", "Run a successful simulation to inspect time samples.");
        drawMessage(rendererState.canvases.projection, "Angular state projection", "No drawable payload is active.");
        updateReadout(body);
        updateFrameIndicator();
        updateScrubber();
        updateControls();
    }

    function titleForStatus(status) {
        if (status === STATUS.STALE) {
            return "Stale output";
        }
        if (status === STATUS.FAILED) {
            return "Output failed";
        }
        if (status === STATUS.CLEARED) {
            return "Output cleared";
        }
        if (status === STATUS.RUNNING) {
            return "Preparing output";
        }
        if (status === "unsupported" || status === "invalid") {
            return "Canvas unavailable";
        }
        return "Simulation output";
    }

    function updateReadoutForFrame() {
        const payload = rendererState.payload;
        const frame = rendererState.selectedFrame;
        const pieces = [
            rendererState.resultStatus === STATUS.STALE ? "Stale run" : "Run",
            String(runIdFrom(payload)),
            "frame",
            String(frame + 1) + "/" + String(payload.sample_count),
            "t = " + formatNumber(payload.time_s[frame], 3) + " s",
            "θ₁ = " + formatNumber(payload.theta1_deg[frame], 2) + " deg",
            "θ₂ = " + formatNumber(payload.theta2_deg[frame], 2) + " deg",
        ];
        if (Array.isArray(payload.omega1_deg_per_s) && Array.isArray(payload.omega2_deg_per_s)) {
            pieces.push("ω₁ = " + formatNumber(payload.omega1_deg_per_s[frame], 2) + " deg/s");
            pieces.push("ω₂ = " + formatNumber(payload.omega2_deg_per_s[frame], 2) + " deg/s");
        } else {
            pieces.push("angular velocity series unavailable");
        }
        updateReadout(pieces.join(" · "));
        updateFrameIndicator();
    }

    function currentFrameSummary() {
        if (!rendererState.payload || !rendererState.metrics) {
            return "";
        }
        const frame = rendererState.selectedFrame;
        const payload = rendererState.payload;
        return [
            "Inspecting frame",
            String(frame + 1) + "/" + String(payload.sample_count),
            "at t = " + formatNumber(payload.time_s[frame], 3) + " s.",
        ].join(" ");
    }

    function updateReadout(message) {
        const readout = rendererState.controls.readout || byId(IDS.readout);
        if (readout) {
            readout.textContent = message || "";
        }
    }

    function updateFrameIndicator(message) {
        const indicator = rendererState.controls.frameIndicator || byId(IDS.frameIndicator);
        if (!indicator) {
            return;
        }
        if (!canInspect()) {
            indicator.textContent = message || "t = --";
            return;
        }
        const payload = rendererState.payload;
        const frame = rendererState.selectedFrame;
        const currentTime = formatNumber(payload.time_s[frame], 1);
        const finalTime = formatNumber(payload.time_s[payload.sample_count - 1], 1);
        indicator.textContent = "t = " + currentTime + " / " + finalTime + " s";
    }

    function updateControls() {
        const controls = rendererState.controls;
        const inspectable = canInspect();
        const playable = canPlay();
        if (controls.play) {
            controls.play.disabled = !playable || rendererState.playing;
        }
        if (controls.pause) {
            controls.pause.disabled = !rendererState.playing;
        }
        if (controls.reset) {
            controls.reset.disabled = !inspectable;
        }
        if (controls.scrubber) {
            controls.scrubber.disabled = !inspectable;
            controls.scrubber.min = 0;
            controls.scrubber.max = inspectable ? Math.max(0, rendererState.metrics.sampleCount - 1) : 0;
            controls.scrubber.step = 1;
            controls.scrubber.value = inspectable ? rendererState.selectedFrame : 0;
        }
        setOptionControlsDisabled(!inspectable);
    }

    function updateScrubber() {
        const scrubber = rendererState.controls.scrubber || byId(IDS.scrubber);
        if (!scrubber) {
            return;
        }
        if (!canInspect()) {
            scrubber.min = 0;
            scrubber.max = 0;
            scrubber.value = 0;
            scrubber.disabled = true;
            return;
        }
        scrubber.min = 0;
        scrubber.max = Math.max(0, rendererState.metrics.sampleCount - 1);
        scrubber.value = rendererState.selectedFrame;
        scrubber.disabled = false;
    }

    function readOptionsFromDom() {
        const controls = rendererState.controls.options;
        if (!controls) {
            return;
        }
        controls.querySelectorAll("input").forEach(function (input) {
            const option = optionNameFromInput(input);
            rendererState.options[option] = Boolean(input.checked);
        });
    }

    function syncOptionsToDom() {
        const controls = rendererState.controls.options;
        if (!controls) {
            return;
        }
        controls.querySelectorAll("input").forEach(function (input) {
            const option = optionNameFromInput(input);
            input.checked = Boolean(rendererState.options[option]);
        });
    }

    function setOptionControlsDisabled(disabled) {
        const controls = rendererState.controls.options;
        if (!controls) {
            return;
        }
        controls.querySelectorAll("input").forEach(function (input) {
            input.disabled = disabled;
        });
    }

    function optionNameFromInput(input) {
        if (!input) {
            return null;
        }
        const namedOption = input.getAttribute("data-canvas-option") || input.value;
        if (namedOption === "axes" || namedOption === "grid") {
            return namedOption;
        }
        return null;
    }

    function scheduleResize() {
        if (rendererState.resizeRaf !== null) {
            return;
        }
        rendererState.resizeRaf = window.requestAnimationFrame(function () {
            rendererState.resizeRaf = null;
            drawAll();
        });
    }

    function canvasContext(canvas) {
        if (!canvas) {
            return null;
        }
        const rect = canvas.getBoundingClientRect();
        const parentRect = canvas.parentElement ? canvas.parentElement.getBoundingClientRect() : rect;
        const width = Math.max(260, Math.floor(rect.width || parentRect.width || 320));
        const height = Math.max(210, Math.floor(rect.height || parentRect.height || 240));
        const ratio = window.devicePixelRatio || 1;
        const pixelWidth = Math.floor(width * ratio);
        const pixelHeight = Math.floor(height * ratio);
        if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
            canvas.width = pixelWidth;
            canvas.height = pixelHeight;
        }
        const ctx = canvas.getContext("2d");
        ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
        return { ctx: ctx, width: width, height: height };
    }

    function clearCanvas(ctx, width, height) {
        ctx.clearRect(0, 0, width, height);
    }

    function drawPanelBackground(ctx, width, height) {
        ctx.fillStyle = PALETTE.white;
        ctx.fillRect(0, 0, width, height);
    }

    function drawGrid(ctx, width, height, step) {
        ctx.save();
        ctx.strokeStyle = PALETTE.grid;
        ctx.lineWidth = 1;
        for (let x = 0; x <= width; x += step) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        }
        for (let y = 0; y <= height; y += step) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
        ctx.restore();
    }

    function drawCrossAxes(ctx, width, height, originX, originY) {
        ctx.save();
        ctx.strokeStyle = PALETTE.axis;
        ctx.lineWidth = 1.25;
        ctx.beginPath();
        ctx.moveTo(originX, 0);
        ctx.lineTo(originX, height);
        ctx.moveTo(0, originY);
        ctx.lineTo(width, originY);
        ctx.stroke();
        ctx.restore();
    }

    function drawBob(ctx, x, y, radius, fillStyle, strokeStyle) {
        ctx.save();
        ctx.fillStyle = fillStyle;
        ctx.strokeStyle = strokeStyle || "rgba(255, 255, 255, 0.92)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        ctx.restore();
    }

    function drawCanvasLabel(ctx, text, x, y) {
        ctx.save();
        ctx.fillStyle = PALETTE.ink;
        ctx.font = "600 13px 'Red Hat Display', Arial, sans-serif";
        ctx.fillText(text, x, y);
        ctx.restore();
    }

    function drawFrameStamp(ctx, width, height) {
        ctx.save();
        ctx.fillStyle = "rgba(255, 255, 255, 0.88)";
        ctx.strokeStyle = PALETTE.grid;
        ctx.lineWidth = 1;
        const text = "Frame " + String(rendererState.selectedFrame + 1) + "/" + String(rendererState.metrics.sampleCount);
        ctx.font = "600 12px 'Red Hat Display', Arial, sans-serif";
        const textWidth = ctx.measureText(text).width;
        ctx.fillRect(width - textWidth - 24, height - 34, textWidth + 14, 22);
        ctx.strokeRect(width - textWidth - 24, height - 34, textWidth + 14, 22);
        ctx.fillStyle = PALETTE.ink;
        ctx.fillText(text, width - textWidth - 17, height - 19);
        ctx.restore();
    }

    function drawStaleOverlay(ctx, width, height) {
        if (rendererState.resultStatus !== STATUS.STALE) {
            return;
        }
        ctx.save();
        ctx.fillStyle = PALETTE.staleFill;
        ctx.fillRect(0, 0, width, height);
        ctx.fillStyle = PALETTE.staleText;
        ctx.font = "700 13px 'Red Hat Display', Arial, sans-serif";
        ctx.fillText("Stale output - rerun to play current result", 14, height - 16);
        ctx.restore();
    }

    function squarePlotArea(width, height, margin) {
        const availableWidth = Math.max(1, width - margin.left - margin.right);
        const availableHeight = Math.max(1, height - margin.top - margin.bottom);
        const size = Math.max(1, Math.min(availableWidth, availableHeight));
        const left = margin.left + (availableWidth - size) / 2;
        const top = margin.top + (availableHeight - size) / 2;
        return {
            left: left,
            right: left + size,
            top: top,
            bottom: top + size,
            width: size,
            height: size,
        };
    }

    function plotArea(width, height, margin) {
        return {
            left: margin.left,
            right: width - margin.right,
            top: margin.top,
            bottom: height - margin.bottom,
            width: width - margin.left - margin.right,
            height: height - margin.top - margin.bottom,
        };
    }

    function motionMapper(plot, range) {
        const scale = plot.width / Math.max(1e-9, range.max - range.min);
        return function (x, y) {
            return {
                x: plot.left + (Number(x) - range.min) * scale,
                y: plot.bottom - (Number(y) - range.min) * scale,
            };
        };
    }

    function niceStep(rawStep) {
        const step = Math.abs(Number(rawStep)) || 1;
        const exponent = Math.floor(Math.log10(step));
        const base = step / Math.pow(10, exponent);
        const niceBase = base <= 1 ? 1 : base <= 2 ? 2 : base <= 5 ? 5 : 10;
        return niceBase * Math.pow(10, exponent);
    }

    function ticksForRange(range, targetCount) {
        const span = Math.max(1e-9, range.max - range.min);
        const step = niceStep(span / Math.max(1, targetCount || 6));
        const ticks = [];
        const start = Math.ceil(range.min / step) * step;
        for (let value = start; value <= range.max + step * 0.5; value += step) {
            if (value >= range.min - step * 0.5 && value <= range.max + step * 0.5) {
                ticks.push(Number(value.toFixed(6)));
            }
        }
        return ticks;
    }

    function formatTick(value) {
        const number = Number(value);
        if (!Number.isFinite(number)) {
            return "";
        }
        if (Math.abs(number) >= 10 || Number.isInteger(number)) {
            return String(Math.round(number));
        }
        return number.toFixed(1);
    }

    function drawMotionGrid(ctx, plot, range, map) {
        const ticks = ticksForRange(range, 6);
        ctx.save();
        ctx.strokeStyle = PALETTE.gridFine;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ticks.forEach(function (tick) {
            const verticalTop = map(tick, range.max);
            const verticalBottom = map(tick, range.min);
            const horizontalLeft = map(range.min, tick);
            const horizontalRight = map(range.max, tick);
            ctx.moveTo(verticalTop.x, verticalTop.y);
            ctx.lineTo(verticalBottom.x, verticalBottom.y);
            ctx.moveTo(horizontalLeft.x, horizontalLeft.y);
            ctx.lineTo(horizontalRight.x, horizontalRight.y);
        });
        ctx.stroke();
        ctx.strokeStyle = PALETTE.grid;
        ctx.strokeRect(plot.left, plot.top, plot.width, plot.height);
        ctx.restore();
    }

    function drawMotionAxes(ctx, plot, range, map) {
        const xAxisStart = map(range.min, 0);
        const xAxisEnd = map(range.max, 0);
        const yAxisStart = map(0, range.min);
        const yAxisEnd = map(0, range.max);
        const ticks = ticksForRange(range, 6);

        ctx.save();
        ctx.strokeStyle = PALETTE.axis;
        ctx.lineWidth = 1.25;
        ctx.beginPath();
        ctx.moveTo(plot.left, xAxisStart.y);
        ctx.lineTo(plot.right, xAxisEnd.y);
        ctx.moveTo(yAxisStart.x, plot.bottom);
        ctx.lineTo(yAxisEnd.x, plot.top);
        ctx.stroke();

        ctx.fillStyle = PALETTE.muted;
        ctx.font = "500 10.5px 'Red Hat Display', Arial, sans-serif";
        ctx.textAlign = "center";
        ticks.forEach(function (tick) {
            const xTick = map(tick, 0);
            if (xTick.x >= plot.left + 2 && xTick.x <= plot.right - 2) {
                ctx.fillText(formatTick(tick), xTick.x, plot.bottom + 14);
            }
            const yTick = map(0, tick);
            if (yTick.y >= plot.top + 2 && yTick.y <= plot.bottom - 2 && Math.abs(tick) > 1e-9) {
                ctx.textAlign = "right";
                ctx.fillText(formatTick(tick), plot.left - 6, yTick.y + 3);
                ctx.textAlign = "center";
            }
        });

        ctx.fillStyle = PALETTE.ink;
        ctx.font = "700 12px 'Red Hat Display', Arial, sans-serif";
        ctx.fillText("x", (plot.left + plot.right) / 2, plot.bottom + 30);
        ctx.save();
        ctx.translate(plot.left - 28, (plot.top + plot.bottom) / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText("y", 0, 0);
        ctx.restore();
        ctx.restore();
    }

    function drawMotionTrace(ctx, payload, map, frame) {
        const step = Math.max(1, Math.floor(Number(payload.sample_count || 1) / 700));
        const drawTrace = function (xValues, yValues, color, width) {
            ctx.save();
            ctx.strokeStyle = color;
            ctx.lineWidth = width;
            ctx.lineCap = "round";
            ctx.lineJoin = "round";
            ctx.beginPath();
            for (let index = 0; index <= frame; index += step) {
                const point = map(Number(xValues[index]), Number(yValues[index]));
                if (index === 0) {
                    ctx.moveTo(point.x, point.y);
                } else {
                    ctx.lineTo(point.x, point.y);
                }
            }
            if (frame > 0 && frame % step !== 0) {
                const point = map(Number(xValues[frame]), Number(yValues[frame]));
                ctx.lineTo(point.x, point.y);
            }
            ctx.stroke();
            ctx.restore();
        };

        drawTrace(payload.x1, payload.y1, PALETTE.traceSoft, 1.2);
        drawTrace(payload.x2, payload.y2, PALETTE.trace, 1.5);
    }

    function scaleLinear(domain, range) {
        const domainSpan = domain.max - domain.min || 1;
        const rangeSpan = range.max - range.min;
        return function (value) {
            return range.min + ((Number(value) - domain.min) / domainSpan) * rangeSpan;
        };
    }

    function drawPlotScaffold(ctx, plot, xLabel, yLabel, options) {
        const xOffset = options && Number.isFinite(Number(options.xOffset)) ? Number(options.xOffset) : 28;
        const yOffset = options && Number.isFinite(Number(options.yOffset)) ? Number(options.yOffset) : 32;
        ctx.save();
        ctx.fillStyle = PALETTE.ink;
        ctx.font = "600 12px 'Red Hat Display', Arial, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(xLabel, (plot.left + plot.right) / 2, plot.bottom + xOffset);
        ctx.save();
        ctx.translate(plot.left - yOffset, (plot.top + plot.bottom) / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText(yLabel, 0, 0);
        ctx.restore();
        ctx.restore();
    }

    function drawPlotGrid(ctx, plot, columns, rows) {
        ctx.save();
        ctx.strokeStyle = PALETTE.grid;
        ctx.lineWidth = 1;
        for (let index = 0; index <= columns; index += 1) {
            const x = plot.left + (plot.width * index) / columns;
            ctx.beginPath();
            ctx.moveTo(x, plot.top);
            ctx.lineTo(x, plot.bottom);
            ctx.stroke();
        }
        for (let index = 0; index <= rows; index += 1) {
            const y = plot.top + (plot.height * index) / rows;
            ctx.beginPath();
            ctx.moveTo(plot.left, y);
            ctx.lineTo(plot.right, y);
            ctx.stroke();
        }
        ctx.restore();
    }

    function drawPlotAxes(ctx, plot) {
        ctx.save();
        ctx.strokeStyle = PALETTE.axis;
        ctx.lineWidth = 1.25;
        ctx.beginPath();
        ctx.moveTo(plot.left, plot.top);
        ctx.lineTo(plot.left, plot.bottom);
        ctx.lineTo(plot.right, plot.bottom);
        ctx.stroke();
        ctx.restore();
    }

    function drawZeroAxes(ctx, plot, xRange, yRange, mapX, mapY) {
        ctx.save();
        ctx.strokeStyle = "rgba(13, 41, 90, 0.42)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        if (xRange.min < 0 && xRange.max > 0) {
            const zeroX = mapX(0);
            ctx.moveTo(zeroX, plot.top);
            ctx.lineTo(zeroX, plot.bottom);
        }
        if (yRange.min < 0 && yRange.max > 0) {
            const zeroY = mapY(0);
            ctx.moveTo(plot.left, zeroY);
            ctx.lineTo(plot.right, zeroY);
        }
        ctx.stroke();
        ctx.restore();
    }

    function drawPlotTickLabels(ctx, plot, xRange, yRange, mapX, mapY) {
        const xTicks = ticksForRange(xRange, 5);
        const yTicks = ticksForRange(yRange, 5);

        ctx.save();
        ctx.strokeStyle = PALETTE.grid;
        ctx.fillStyle = PALETTE.muted;
        ctx.lineWidth = 1;
        ctx.font = "500 10.5px 'Red Hat Display', Arial, sans-serif";

        ctx.beginPath();
        xTicks.forEach(function (tick) {
            const x = mapX(tick);
            if (x >= plot.left - 0.5 && x <= plot.right + 0.5) {
                ctx.moveTo(x, plot.bottom);
                ctx.lineTo(x, plot.bottom + 4);
            }
        });
        yTicks.forEach(function (tick) {
            const y = mapY(tick);
            if (y >= plot.top - 0.5 && y <= plot.bottom + 0.5) {
                ctx.moveTo(plot.left - 4, y);
                ctx.lineTo(plot.left, y);
            }
        });
        ctx.stroke();

        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        xTicks.forEach(function (tick) {
            const x = mapX(tick);
            if (x >= plot.left - 0.5 && x <= plot.right + 0.5) {
                ctx.fillText(formatTick(tick), x, plot.bottom + 7);
            }
        });

        ctx.textAlign = "right";
        ctx.textBaseline = "middle";
        yTicks.forEach(function (tick) {
            const y = mapY(tick);
            if (y >= plot.top - 0.5 && y <= plot.bottom + 0.5) {
                ctx.fillText(formatTick(tick), plot.left - 8, y);
            }
        });
        ctx.restore();
    }

    function drawLineSeries(ctx, xValues, yValues, mapX, mapY, color) {
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        for (let index = 0; index < xValues.length; index += 1) {
            const x = mapX(Number(xValues[index]));
            const y = mapY(Number(yValues[index]));
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }
        ctx.stroke();
        ctx.restore();
    }

    function drawCursor(ctx, x, top, bottom) {
        ctx.save();
        ctx.strokeStyle = "rgba(13, 41, 90, 0.82)";
        ctx.lineWidth = 1.5;
        ctx.setLineDash([5, 4]);
        ctx.beginPath();
        ctx.moveTo(x, top);
        ctx.lineTo(x, bottom);
        ctx.stroke();
        ctx.restore();
    }

    function drawLegend(ctx, x, y, items) {
        ctx.save();
        ctx.font = "600 12px 'Red Hat Display', Arial, sans-serif";
        let offset = 0;
        items.forEach(function (item) {
            const label = item[0];
            const color = item[1];
            ctx.fillStyle = color;
            ctx.fillRect(x + offset, y - 9, 18, 3);
            ctx.fillStyle = PALETTE.ink;
            ctx.fillText(label, x + offset + 24, y - 5);
            offset += 78;
        });
        ctx.restore();
    }

    function drawMessage(canvas, title, body) {
        const panel = canvasContext(canvas);
        if (!panel) {
            return;
        }
        const ctx = panel.ctx;
        const width = panel.width;
        const height = panel.height;
        clearCanvas(ctx, width, height);
        drawPanelBackground(ctx, width, height);
        drawGrid(ctx, width, height, 42);
        ctx.save();
        ctx.fillStyle = PALETTE.ink;
        ctx.font = "700 15px 'Red Hat Display', Arial, sans-serif";
        ctx.fillText(title, 18, 34);
        ctx.font = "500 13px 'Red Hat Display', Arial, sans-serif";
        wrapText(ctx, body || "", 18, 62, width - 36, 18);
        ctx.restore();
    }

    function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
        const words = String(text).split(/\s+/);
        let line = "";
        let currentY = y;
        words.forEach(function (word) {
            const testLine = line ? line + " " + word : word;
            if (ctx.measureText(testLine).width > maxWidth && line) {
                ctx.fillText(line, x, currentY);
                line = word;
                currentY += lineHeight;
            } else {
                line = testLine;
            }
        });
        if (line) {
            ctx.fillText(line, x, currentY);
        }
    }

    function setShellStatus(status) {
        if (!rendererState.shell) {
            return;
        }
        rendererState.shell.setAttribute("data-result-state", status || STATUS.EMPTY);
        const workspace = rendererState.controls.workspace || byId(IDS.workspace);
        if (workspace) {
            workspace.setAttribute("data-result-state", status || STATUS.EMPTY);
        }
    }

    function formatNumber(value, digits) {
        const number = Number(value);
        if (!Number.isFinite(number)) {
            return "n/a";
        }
        return number.toFixed(digits);
    }

    function destroy() {
        cancelPlayback("cancelled");
        rendererState.payload = null;
        rendererState.metrics = null;
        rendererState.activePayloadKey = null;
        rendererState.activeRunId = null;
    }

    function start() {
        if (init() && !rendererState.payload) {
            renderNonDrawable(STATUS.EMPTY, "No simulation run yet.");
        }
        if (!rendererState.observer && document.body) {
            rendererState.observer = new MutationObserver(function () {
                if (!hasShell()) {
                    cancelPlayback("cancelled");
                    rendererState.shell = null;
                    rendererState.boundShell = null;
                    return;
                }
                init();
            });
            rendererState.observer.observe(document.body, { childList: true, subtree: true });
        }
    }

    window.DoublePendulumCanvasRenderer = {
        applyState: applyState,
        init: init,
        play: play,
        pause: pause,
        reset: reset,
        scrub: scrub,
        setOptions: setOptions,
        destroy: destroy,
        _state: rendererState,
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
}());
