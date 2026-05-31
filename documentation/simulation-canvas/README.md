# Simulation Canvas Architecture

This folder documents the current Canvas-backed Simulation architecture.

These files are durable implementation references for the live `/simulation`
page. They are not exploratory workbench notes and not a product roadmap.

Use this folder before changing:

- the Canvas payload schema;
- Simulation result statuses;
- Dash stores used by Simulation rendering;
- callback flow for run, stale, failed, empty, cleared, or successful states;
- browser-side Canvas rendering, playback, or selected-frame inspection;
- Hamiltonian state-convention handling in displayed payloads.

## Index

- [Canvas Integration API](canvas-integration-api.md)
- [Simulation Result Contract](simulation-result-contract.md)
- [Callback Rendering Flow](callback-rendering-flow.md)

## Boundary

Python owns mathematical and numerical truth. Dash callbacks and stores deliver
validated payloads. Browser-side JavaScript/Canvas owns rendering, playback,
resize behavior, and selected-frame inspection only.

JavaScript must not integrate trajectories, compute physics, infer Hamiltonian
angular velocities, or transform solver state conventions.

Historical evidence for why this architecture was accepted remains under
`../../development/simulation_workbench/`. Active phase planning lives in
`../../ROADMAP.md`.
