---
name: jambro-beamer-setup
description: Scaffold new Beamer presentations that use the bundled Jambro theme (`beamerthemejambro.sty`). Use when Codex needs to create or set up a presentation folder, starter `.tex` deck, or self-contained Beamer template based on Jambro, especially when the presentation should default to the red theme and optionally expose Jambro features such as `3to2`, `shownotes`, `handout2x1`, `onesec`, annotations, code boxes, and table helpers.
---

# Jambro Beamer Setup

## Overview

Create a self-contained Beamer presentation folder using the bundled Jambro theme asset and a minimal red starter deck. Keep the default scaffold generic and 16:9, and only pull in richer demo features when the user asks for them.

## Workflow

1. Confirm the target directory and the output `.tex` filename.
2. Copy these two assets into the target presentation folder:
   - `assets/beamerthemejambro.sty`
   - `assets/jambro-red-starter.tex`
3. Rename `jambro-red-starter.tex` to the requested deck filename.
4. Update the deck metadata:
   - `\title[...]{}`
   - `\subtitle{}`
   - `\author{}`
   - `\institute{}`
   - `\date{}`
5. Leave the default class line as `\documentclass[red]{beamer}` unless the user explicitly asks for a different theme option.
6. Keep the theme file in the same folder as the presentation unless the user specifically wants a local TeX tree install.
7. Compile only if the user asks for a build or if a smoke test is useful to verify the scaffold.

## Defaults

- Default to the Jambro red palette via `red`.
- Default to Jambro's standard 16:9 layout. Add `3to2` only when requested.
- Keep the starter generic:
  - title slide
  - overview slide
  - one standard content slide
  - one figure placeholder slide
  - one `fragile` code/example slide
- Do not import course-specific structure, package stacks, or content from other decks.

## Optional Theme Options

Add these only when the user asks for them:

- `3to2`: switch from 16:9 to 3:2
- `shownotes`: show speaker notes pages
- `handout2x1`: render 2-up handouts for printing
- `onesec`: show only the current section in the footline
- `night`: switch to the dark palette
- `cabin`: use Cabin as the sans font
- `roboto`: use Roboto as the sans font
- `light`: use the light variant for supported fonts

## Advanced Features

Read `references/demo-feature-map.md` when the user wants to go beyond the starter and needs examples from `JambroBeamerTheme/Demo.tex`, including:

- speaker notes or handouts
- handwritten annotations and arrows
- highlighting or pencil boxes
- bubble callouts
- code boxes
- table layout helpers

## Assets

- `assets/beamerthemejambro.sty`: bundled Jambro theme file for self-contained setups
- `assets/jambro-red-starter.tex`: minimal starter deck that defaults to the red palette

## Guardrails

- Do not overwrite an existing deck without explicit user intent.
- Preserve user content if the task is to retrofit Jambro into an existing presentation rather than create a new one.
- Keep the starter self-contained: it should compile with only the copied `.tex` file and the colocated `beamerthemejambro.sty`.
