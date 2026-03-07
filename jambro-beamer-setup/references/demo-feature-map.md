# Jambro Demo Feature Map

Use this file only when the user wants features beyond the minimal red starter deck. The source of truth for examples is `JambroBeamerTheme/Demo.tex`.

## Notes and Handouts

- Use when the user wants speaker notes, printable handouts, or both.
- Add `shownotes` to the `\documentclass[...]` options to expose note pages.
- Add `handout2x1` when the user wants 2-up printable handouts.
- Use `\shownotesblock{...}` for standard slides and `\shownotesblockzero{...}` for the title slide.

## Handwritten Annotations and Arrows

- Use when the user wants callouts pointing to a term, equation, or plotted object.
- `\marker{node}{text}` creates an anchor in regular content.
- `\lapisnote[options]{node}{text}` is the fastest way to attach a handwritten annotation.
- For fully custom annotations, use a `tikzpicture` with the theme's `arrow` or `snake` styles.

## Highlighting and Boxing

- Use `\hl{...}` or `\stabilo{...}` for highlight-style emphasis.
- Use `\lapis{...}` for a pencil underline.
- Use `\lapisbox{...}` or `\lapisbox[color=...,label=...]{...}` to box text, equations, or table cells.
- Prefer these when emphasis should match the theme instead of standard Beamer blocks.

## Bubble Callouts

- Use `\NB{...}` for inline callout bubbles.
- Pass a width like `\NB[0.6\textwidth]{...}` when the bubble should not span the full line.

## Code Blocks

- Use a `fragile` frame whenever the slide contains verbatim content.
- `\jverb{...}` works for inline code.
- `jVerb` works for verbatim blocks.
- `\jCode{...}` works for compact highlighted code boxes without raw verbatim syntax.

## Tables and Figure Helpers

- Use `\tablesize` before dense tables.
- Use `tabularx` with `Y` for centered auto-width columns.
- Use `S` for de-emphasized gray columns.
- Use `\sym{***}` for significance stars in tables.
- Use `\notesize`-style note text under figures or tables for source notes.

## Theme Options

- `red` changes the palette from blue to red.
- `3to2` switches the slide geometry to 3:2.
- `onesec` simplifies the footline to the current section only.
- `night`, `cabin`, `roboto`, and `light` change the look without changing slide structure.
