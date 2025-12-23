# Peptide AI Chrome Extension

Quick access to peptide research from your browser.

## Features

- **Popup Chat**: Ask questions about peptides directly from the extension
- **Reddit Integration**: Highlights peptide mentions on r/peptides, r/nootropics, etc.
- **Quick Actions**: One-click access to common peptide queries
- **Streaming Responses**: Real-time responses with source citations

## Installation

### For Development

1. **Generate Icons** (required first time):
   - Open `icons/generate-icons.html` in Chrome
   - Click each "Download" button
   - Save the PNGs in the `icons/` folder

2. **Load Extension**:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode" (top right)
   - Click "Load unpacked"
   - Select this `extension` folder

3. **Test**:
   - Click the extension icon in your toolbar
   - Try asking about BPC-157 or Semaglutide
   - Visit r/peptides to see highlighted mentions

### For Distribution

1. Generate production icons (or use proper designer icons)
2. Zip the extension folder
3. Submit to Chrome Web Store

## Files

```
extension/
├── manifest.json      # Extension config
├── popup.html         # Main popup UI
├── popup.js           # Popup logic
├── content.js         # Reddit integration
├── content.css        # Highlight styles
├── icons/
│   ├── icon16.png
│   ├── icon32.png
│   ├── icon48.png
│   └── icon128.png
└── README.md
```

## API Configuration

The extension connects to:
- **API**: `https://peptide-ai-api-production.up.railway.app`
- **Web**: `https://peptide-ai-web-production.up.railway.app`

No API key is required for basic usage (uses anonymous rate-limited access).

## Permissions

- `storage`: Save user preferences
- `activeTab`: Read current page for context
- Reddit host access: For peptide highlighting
