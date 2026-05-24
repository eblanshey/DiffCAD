# Translations

This directory contains translation sources and compiled binaries for the History workbench.

## Files

- `History.ts`: base template extracted from source code.
- `History_<locale>.ts`: locale translation source files, for example `History_de.ts`.
- `History_<locale>.qm`: compiled locale binaries generated from locale `.ts` files.

## Update Translation Template

Use Taskfile task:

```bash
task translations:update
```

Equivalent direct command:

```bash
lupdate -extensions py freecad/history_wb -ts freecad/history_wb/resources/translations/History.ts
```

## Compile Locale Files

Use Taskfile task:

```bash
task translations:compile
```

Equivalent direct command for specific locales:

```bash
lrelease freecad/history_wb/resources/translations/History_de.ts
```

`translations:compile` skips cleanly when no locale files exist.

## Update Locale Sources

Use Taskfile task:

```bash
task translations:update-locales
```

Equivalent direct command for one locale file:

```bash
lupdate -extensions py freecad/history_wb -ts freecad/history_wb/resources/translations/History_de.ts
```

Run this after changing user-facing strings so locale `.ts` files receive new and obsolete entries.

## Refresh All

Use Taskfile task:

```bash
task translations:refresh
```

This updates `History.ts`, merges new strings into locale `.ts` files, and compiles locale `.ts` files.

## Repository Policy

Commit `History.ts` and locale `.ts` files.
Commit locale `.qm` files when locale translations exist.
