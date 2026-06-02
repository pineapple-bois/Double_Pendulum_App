# Chaos Fidelity Review Questions

Use this checklist before rewriting or promoting any Chaos page artifact.

## Mathematical Definition

- Which model is in scope: simple, compound, or both?
- Which formulation is in scope: Lagrangian state or Hamiltonian state?
- What is the exact state vector order?
- What are the units for each state component?
- What is the conserved quantity being checked, and relative to which datum?
- Is the artifact qualitative teaching material, quantitative diagnostic
  material, or both?

## Poincare Sections

- What is the section equation?
- Is crossing direction filtered?
- Which variable is plotted on each axis?
- Which momentum is conjugate to the plotted coordinate?
- How are crossings interpolated between solver samples?
- Are angle wraps normalized before plotting?
- Are section points rejected based on energy drift, solver failure, or event
  termination?

## Numerical Contract

- Which solver method and tolerances are used?
- Is there a high-accuracy reference run?
- Are tolerance-sensitivity and solver-method comparisons recorded?
- What energy-drift threshold is acceptable?
- Are failed, terminated, or incomplete simulations excluded rather than padded
  into apparently valid data?
- Are float precision reductions justified?

## Data And UX

- Is the output schema versioned?
- Is every dataset tied to parameters, solver policy, and validation results?
- Are user-facing filters pedagogical or merely compute-saving?
- Can the artifact be explained without implying stronger mathematical proof
  than was performed?
- Does the page communicate numerical caution where appropriate?

