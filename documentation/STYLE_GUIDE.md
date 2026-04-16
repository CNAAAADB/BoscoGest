# BoscoGest Frontend - Style Guide

Reference for maintaining visual consistency across all views.

## Color Palette

| Token | Value | Usage |
|---|---|---|
| Primary | `#3D4E7C` | Page titles, table headers, buttons, nav accents |
| Primary Hover | `#2C3E5A` | Button hover states |
| Accent / Icon | `#D4A76A` | Section title icons (`.title-icon`) |
| Text Primary | `#1b1b1b` | Table cell names, strong text |
| Text Secondary | `#495057` | Table cells, body text |
| Text Muted | `#6c757d` | Descriptions, empty states |
| Border | `#e9ecef` | Card borders, header dividers |
| Background | `#f4f7fa` | Layout content area (set in `layout.component.css`) |
| Table Header BG | `#f8f9fa` | Table header row background |
| Card Background | `white` | All cards, dialogs |

## Container Pattern

Every view's root container **must** follow this pattern:

```css
.{view}-container {
  padding: 2rem;
  width: 100%;
  min-height: 100%;
  box-sizing: border-box;
}
```

**Do NOT use** `max-width` or `margin: 0 auto` on view containers. Views should stretch to fill the available width within the layout.

### Responsive breakpoint

```css
@media (max-width: 768px) {
  .{view}-container {
    padding: 1rem;
  }
}
```

## Page Title

```css
.page-title {
  font-size: 2.5rem;
  font-weight: 600;
  color: #3D4E7C;
  margin-bottom: 2rem;
}

/* Responsive */
@media (max-width: 768px) {
  .page-title {
    font-size: 2rem;
  }
}
```

## Cards (mat-card)

All `mat-card` components receive a white background globally via `styles.css`:

```css
.mat-mdc-card {
  background-color: white !important;
}
```

No per-component `background-color` override is needed for cards. The global rule ensures every `mat-card` is white regardless of the Angular Material theme.

### List view cards (table wrappers)

```css
.{view}-card {
  margin-bottom: 2rem;
  border-radius: 8px;
  box-shadow: none;
  border: 1px solid #e9ecef;
}
```

### Detail/Form view cards

```css
.{view}-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
```

### Grid item cards (magazines, resources, activities)

```css
.{item}-card {
  border: 1px solid #e9ecef;
  /* other card-specific styles */
}
```

## Card Header & Section Title

```css
mat-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e9ecef;
}

.section-title {
  display: flex !important;
  align-items: center !important;
  gap: 0.75rem !important;
  font-size: 1.5rem !important;
  font-weight: 600 !important;
  margin: 0 !important;
}

.title-icon {
  color: #D4A76A;
  font-size: 1.75rem !important;
  width: 1.75rem !important;
  height: 1.75rem !important;
}
```

## Tables

```css
.table-header {
  font-size: 1.125rem !important;
  font-weight: 600 !important;
  color: #3D4E7C !important;
  background-color: #f8f9fa;
  padding: 1rem !important;
}

.table-cell {
  padding: 1rem !important;
  font-size: 1.125rem;
  color: #495057;
}

.name-cell {
  font-weight: 600;
  color: #1b1b1b;
}
```

## Action Buttons (in tables)

```css
.action-button {
  width: 40px !important;
  height: 40px !important;
  transition: all 0.2s ease;
}

.view-button  { color: #667eea !important; }
.edit-button  { color: #fd7e14 !important; }
.delete-button { color: #dc3545 !important; }
```

## Loading Spinner

```css
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
  padding: 2rem;
}
```

## Empty State

```css
.empty-state {
  text-align: center;
  color: #6c757d;
  font-size: 1.25rem;
  padding: 2rem;
  margin: 0;
}
```

## Dialogs / Modals

All dialogs get a white background globally via `styles.css`:

```css
.mat-mdc-dialog-container .mdc-dialog__surface {
  background-color: white !important;
}
```

No per-component `::ng-deep` overrides are needed for dialog backgrounds.

## Units

Always use `rem` for spacing and sizing. Never use `px` for paddings, margins, gaps, or font-sizes in component CSS.

**Exception**: Internal Material component overrides (color pickers, drag handles) may keep `px` when tied to specific pixel-aligned elements.

## Status Chips

```css
.status-chip.active {
  background-color: #d4edda !important;
  color: #155724 !important;
}

.status-chip.inactive {
  background-color: #f8d7da !important;
  color: #721c24 !important;
}
```

## Form Views

Form containers follow the same base container pattern. The form card uses the detail/form card style:

```css
.form-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  background-color: white !important;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e0e0e0;
}
```

## Checklist for New Views

1. Container uses `width: 100%; min-height: 100%; box-sizing: border-box; padding: 2rem;`
2. No `max-width` or `margin: 0 auto` on the container
3. Page title uses `color: #3D4E7C; font-size: 2.5rem; font-weight: 600;`
4. Cards get `background-color: white` from global `styles.css` — no per-component override needed
5. List cards: `border: 1px solid #e9ecef; box-shadow: none; border-radius: 8px;`
6. Detail/form cards: `box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 12px;`
7. Title icons use `color: #D4A76A`
8. Table headers use `color: #3D4E7C`
9. All spacing in `rem`, not `px`
10. Responsive breakpoint at `768px` reduces container padding to `1rem`
