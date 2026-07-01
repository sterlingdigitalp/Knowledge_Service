# Frontend Verification

## Screens

- Screen 1: Morning Intelligence
- Screen 2: Intelligence Profiles
- Removed: Archive screen, Brief/Archive toggle, dashboard-style navigation
- Permanent Morning Intelligence home: `frontend/latest.html`
- Backend refresh contract: overwrite only `frontend/latest.html` after each new Morning Brief
- `latest.html` is self-contained for direct `file://` opening

## Screenshot Gallery

See [SCREENSHOT_GALLERY.md](./SCREENSHOT_GALLERY.md).

## Copy Workflow Demonstration

Tested `Copy AI Prompt` on the first Intelligence Item. The copied block includes:

- title
- executive summary
- why it matters
- historical context
- evidence
- timestamp links
- suggested exploration questions
- source URLs

The copied prompt begins:

```text
Prepare a 10-20 minute verbal analyst explanation of this intelligence item for me.

Title: Biden Developments
Executive summary: 2 independent sources...
```

## Browser Compatibility

- Uses a single self-contained `latest.html` with inline CSS, inline JavaScript, and embedded Morning Brief data.
- Uses `prefers-color-scheme` for light and dark mode.
- Uses `navigator.clipboard.writeText` with a textarea fallback for older or restricted browsers.
- Uses `localStorage` for Intelligence Profiles edits.
- Does not require localhost, IP addresses, npm, or a development server.

## Test Results

- Latest runtime Morning Brief embedded into `latest.html`: pass.
- Permanent `latest.html` entrypoint generated: pass.
- `latest.html` contains embedded Morning Intelligence data: pass.
- `latest.html` contains inline CSS and inline JavaScript: pass.
- `latest.html` contains no `fetch()` call: pass.
- `latest.html` contains no external script or stylesheet references: pass.
- `latest.html` contains no `data/current.json` dependency: pass.
- Python data builder syntax check: pass.
- JavaScript syntax check: pass.
- Morning Intelligence renders 5 items: pass.
- Date dropdown is present and Archive screen is absent: pass.
- Profiles page renders AI, Investing, Founders, and Longevity: pass.
- Profiles page exposes exactly 12 editable sections: pass.
- Copy AI Prompt includes timestamp links and URLs: pass.
- Desktop layout horizontal overflow: none detected.
- Mobile layout horizontal overflow: none detected.
