# 0002 — Shared harness, task-owned semantics

**Status:** Accepted  
**Date:** 2026-08-30

## Context

Glideator has multiple ML problems with fundamentally different data and evaluation semantics: site discovery, XC potential, and analogous-day retrieval.

A highly generic ML abstraction would reduce duplicated plumbing, but forcing data preparation, metrics, models, and artifact contracts behind one common interface would hide important domain differences and make the code harder to reason about.

## Decision

Share only the experiment infrastructure that is genuinely common: CLI/config loading, provenance, tracking, and repository conventions.

Each task owns:

- data preparation and splitting;
- benchmark definitions;
- evaluation logic;
- models;
- artifact and serving contract.

## Why

The goal of the ml/ workspace is comparable, reproducible experiments — not making every model family look structurally identical.

Keeping task semantics local makes leakage rules, metric meaning, and serving assumptions visible where they matter.

## Consequences

- Task evaluators may intentionally differ.
- New tasks should not inherit a generic metric abstraction unless a real shared abstraction emerges.
- Documentation mirrors code ownership: each task has its own methodology and model catalogue.
