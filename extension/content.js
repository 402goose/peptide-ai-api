// Peptide AI Content Script
// Runs on Reddit to highlight peptide mentions and provide quick access

const PEPTIDES = [
  'BPC-157', 'BPC157', 'TB-500', 'TB500', 'Thymosin Beta-4',
  'Semaglutide', 'Ozempic', 'Wegovy', 'Tirzepatide', 'Mounjaro', 'Zepbound',
  'GHK-Cu', 'GHK', 'Ipamorelin', 'CJC-1295', 'CJC1295',
  'GHRP-6', 'GHRP-2', 'Melanotan', 'MT-2', 'PT-141', 'Bremelanotide',
  'Epitalon', 'Semax', 'Selank', 'Dihexa', 'LL-37', 'MOTS-c',
  'AOD-9604', 'Thymosin Alpha-1', 'SS-31', 'Elamipretide'
];

const WEB_URL = 'https://peptide-ai-web-production.up.railway.app';

// Create tooltip element
function createTooltip() {
  const tooltip = document.createElement('div');
  tooltip.id = 'peptide-ai-tooltip';
  tooltip.innerHTML = `
    <div style="
      position: fixed;
      z-index: 10000;
      display: none;
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 8px 12px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 13px;
      color: #e2e8f0;
      max-width: 280px;
    ">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <svg width="16" height="16" viewBox="0 0 32 32" fill="none">
          <rect width="32" height="32" rx="6" fill="#3b82f6"/>
          <path d="M16 8L12 12H14V18H18V12H20L16 8Z" fill="white"/>
        </svg>
        <strong id="peptide-name" style="color:#60a5fa;"></strong>
      </div>
      <p id="peptide-desc" style="margin:0;line-height:1.4;color:#94a3b8;"></p>
      <a id="peptide-link" href="#" target="_blank" style="
        display: inline-block;
        margin-top: 8px;
        padding: 4px 10px;
        background: #3b82f6;
        color: white;
        border-radius: 4px;
        text-decoration: none;
        font-size: 12px;
      ">Learn more on Peptide AI</a>
    </div>
  `;
  document.body.appendChild(tooltip);
  return tooltip.firstElementChild;
}

// Quick descriptions for common peptides
const PEPTIDE_INFO = {
  'BPC-157': 'Body Protection Compound. Research shows potential for gut healing and tissue repair. Animal studies primarily.',
  'TB-500': 'Thymosin Beta-4 fragment. Studied for wound healing and tissue regeneration. Limited human data.',
  'Semaglutide': 'GLP-1 agonist. FDA-approved for diabetes (Ozempic) and weight loss (Wegovy). Strong evidence.',
  'Tirzepatide': 'Dual GIP/GLP-1 agonist. FDA-approved (Mounjaro/Zepbound). Very effective for weight loss.',
  'GHK-Cu': 'Copper peptide. Human studies for skin healing. Found in many cosmetic products.',
  'Ipamorelin': 'Growth hormone secretagogue. Limited human trials. Used for anti-aging research.',
  'CJC-1295': 'GHRH analog. Few human studies on GH release. Often combined with Ipamorelin.',
  'PT-141': 'Bremelanotide. FDA-approved (Vyleesi) for female sexual dysfunction.',
  'Semax': 'ACTH analog. Approved in Russia for stroke/cognitive. Not FDA-approved.',
  'Selank': 'Tuftsin analog. Russian approval for anxiety. Limited Western research.',
};

let tooltip = null;

// Highlight peptide mentions on page
function highlightPeptides() {
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    null,
    false
  );

  const textNodes = [];
  while (walker.nextNode()) {
    if (walker.currentNode.parentElement?.tagName !== 'SCRIPT' &&
        walker.currentNode.parentElement?.tagName !== 'STYLE') {
      textNodes.push(walker.currentNode);
    }
  }

  const regex = new RegExp(`\\b(${PEPTIDES.join('|')})\\b`, 'gi');

  textNodes.forEach(node => {
    const text = node.textContent;
    if (regex.test(text)) {
      const span = document.createElement('span');
      span.innerHTML = text.replace(regex, '<span class="peptide-ai-highlight" data-peptide="$1">$1</span>');
      node.parentNode.replaceChild(span, node);
    }
  });
}

// Add event listeners for highlighted peptides
function addTooltipListeners() {
  if (!tooltip) {
    tooltip = createTooltip();
  }

  document.querySelectorAll('.peptide-ai-highlight').forEach(el => {
    el.addEventListener('mouseenter', (e) => {
      const peptide = e.target.dataset.peptide.toUpperCase();
      const normalizedPeptide = Object.keys(PEPTIDE_INFO).find(p =>
        p.toUpperCase() === peptide || peptide.includes(p.toUpperCase().replace('-', ''))
      ) || peptide;

      const nameEl = tooltip.querySelector('#peptide-name');
      const descEl = tooltip.querySelector('#peptide-desc');
      const linkEl = tooltip.querySelector('#peptide-link');

      nameEl.textContent = normalizedPeptide;
      descEl.textContent = PEPTIDE_INFO[normalizedPeptide] || 'Click to learn more about this peptide.';
      linkEl.href = `${WEB_URL}/chat?q=Tell me about ${encodeURIComponent(normalizedPeptide)}`;

      const rect = e.target.getBoundingClientRect();
      tooltip.style.left = `${rect.left}px`;
      tooltip.style.top = `${rect.bottom + 8}px`;
      tooltip.style.display = 'block';
    });

    el.addEventListener('mouseleave', () => {
      setTimeout(() => {
        if (!tooltip.matches(':hover')) {
          tooltip.style.display = 'none';
        }
      }, 200);
    });
  });

  if (tooltip) {
    tooltip.addEventListener('mouseleave', () => {
      tooltip.style.display = 'none';
    });
  }
}

// Initialize
function init() {
  // Only run on peptide-related subreddits or when peptides are mentioned
  const isPeptideSubreddit = /\/(peptides|nootropics|biohacking|sarms|moreplatesmoredates)/i.test(location.pathname);

  if (isPeptideSubreddit || document.body.textContent.match(/BPC-?157|TB-?500|semaglutide|tirzepatide/i)) {
    highlightPeptides();
    addTooltipListeners();
    console.log('[Peptide AI] Content script initialized');
  }
}

// Run when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Re-run on dynamic content (for infinite scroll)
const observer = new MutationObserver((mutations) => {
  let shouldRerun = false;
  for (const mutation of mutations) {
    if (mutation.addedNodes.length > 0) {
      shouldRerun = true;
      break;
    }
  }
  if (shouldRerun) {
    setTimeout(() => {
      highlightPeptides();
      addTooltipListeners();
    }, 500);
  }
});

observer.observe(document.body, { childList: true, subtree: true });
