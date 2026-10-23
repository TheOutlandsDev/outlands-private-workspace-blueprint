# Original OUTLANDS branding

Give the workspace a consistent black-and-red identity while leaving the app's function easy to understand. The visual direction is cyberpunk-inspired: dark surfaces, restrained signal red, geometric dividers, compact labels, and clear operational status. Create original artwork and wording rather than copying a franchise interface or another project's assets.

This repository's visual examples are illustrative assets. They do not depict a private installation or prove that every linked app has been themed.

## A small design system

| Token | Suggested value | Use |
| --- | --- | --- |
| Background | `#09090B` | Page canvas |
| Surface | `#141418` | Cards and navigation |
| Raised surface | `#1E1E24` | Focused sections and menus |
| Primary text | `#F4F4F5` | Main copy and values |
| Secondary text | `#B6B6C2` | Descriptions and timestamps |
| Accent | `#F43F5E` | Borders, focus cues, selected navigation |
| Warning | `#FBBF24` | Warning state with a text label |

These are starting values, not a completed contrast audit. Check each actual text/background pair, including disabled, hover, focus, error, and mobile states. Use labels and icons alongside color. Keep meaningful focus outlines and respect reduced-motion preferences. A low-glare design should not make small values hard to read.

Use short category names such as Workspace, Observe, and Tools. Pair each tile with a plain description: what it opens, whether it needs another login, and whether it is currently available. An unavailable app should remain understandable without an animation or color legend.

## Apply it to Homepage first

Start with supported title, theme, color, layout, favicon, and background settings. Put the most used categories first and use a stable grouping structure. Homepage documents these settings and its YAML layout options. [Homepage settings](https://gethomepage.dev/configs/settings/)

Use the supported `custom.css` extension point for a small, versioned stylesheet. Scope selectors narrowly and retest after upgrades. Keep the stylesheet free of private URLs, usernames, secrets, and comments about private infrastructure: Homepage documents that this CSS remains publicly accessible when its authentication is enabled. Avoid introducing custom JavaScript when CSS can express the design. [Homepage custom CSS and JavaScript](https://gethomepage.dev/configs/custom-css-js/)

Keep assets local to the deployment when practical. Give original SVG files descriptive names and accessible text equivalents. Confirm that a background remains optional, page text survives a missing image, and the design works without remote fonts or third-party tracking scripts.

## Theme each app on its own terms

Native app theming varies by product, version, and edition. A branded launcher does not automatically restyle Grafana, Authentik, or the other destinations. Prefer documented logo, title, palette, and theme controls. Preserve visible login, error, and logout affordances. Do not replace trusted vendor warnings with decorative text or patch packaged application files to force a theme.

Keep a per-app note with the supported customization, the affected version, and the check required after an upgrade. If an app offers no supported theming, use its native UI and give its catalog tile a consistent OUTLANDS treatment.

## Visual review

Review desktop, narrow browser, and real phone views. Check long app names, empty metrics, stale data, denied access, and loading failures. A screenshot should say **ILLUSTRATIVE MOCKUP** when it contains synthetic data. Crop or redact private information before any approved public capture, and treat the final exported file as the material to review.

Consult [third-party boundaries](third-party.md) before adding logos, fonts, icons, or screenshots.
