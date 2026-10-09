# Lite RaBitQ backend design

The earlier RABITQ enum and VSAGLT01 version-4 proposal is superseded by the actual opt-in RABITQ8 candidate. Its public API and transactional implementation already exist on the personal development branch; upstream promotion and performance acceptance remain incomplete.

Canonical design (audited 2026-10-09):

- [English](../../docs/docs/en/src/development/lite_rabitq_design.md)
- [中文](../../docs/docs/zh/src/development/lite_rabitq_design.md)

The design records actual VSAGLQ01 v1 layout, fixed 3+5 profile, temporary floating construction cost, journaled CRUD limits, measured evidence, next optimization steps and promotion gates. Do not use the old proposal as an implementation specification. PR #2904 does not yet contain this candidate.
