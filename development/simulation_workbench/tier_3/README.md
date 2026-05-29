# Tier 3 Animation And Interaction

Tier 3 investigates the expensive and fragile parts of the future Simulation
workspace: animation lifecycle, motion rendering, play/pause/reset/scrub
behavior, stale-state prevention, and renderer choice.

The Tier 3 root is only for roadmap and index material. Each investigation
belongs in its own sub-tier directory.

Planned sub-tiers:

- `tier_3a_animation_lifecycle/` - closed; `unique graph per run` fixed the known Plotly stale-playback bug by manual inspection and was promoted to production.
- `tier_3b_plotly_strategies/` - parked after first evidence pass; reduced frames rejected, selected-time inspection is the strongest signal.
- `tier_3c_canvas_feasibility/` - closed for now after Canvas-native synced inspection; Canvas is a stronger production candidate but not yet production-approved.
- `tier_3d_interaction_contract/` - complete first pass; state, event, stale-output, run ID, and selected-frame contract.
- `tier_3e_renderer_decision/` - accepted handoff; Canvas renderer API, stress checks, recommendation, and promotion plan.

The initial Tier 3A scaffold did not change production. A later explicit
promotion task wired the accepted `unique graph per run` mitigation into the
production `/simulation` page without changing component IDs, CSS, model
behavior, plotting behavior, or solver behavior.

Start with `TIER_3_ROADMAP.md`, then the Tier 3C.2 synced-inspection note, the
Tier 3D event matrix, and the accepted Tier 3E renderer decision. Production
promotion planning now continues in `../tier_4_production_promotion/`.
