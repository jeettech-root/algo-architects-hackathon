const STORAGE_KEY = 'cybershieldLastScan';
const SCAN_COOLDOWN_MS = 60 * 1000;
const AUTO_SCAN_MIN_TEXT_LENGTH = 80;
const AUTO_SCAN_DELAY_MS = 1200;
const PAGE_SCAN_KEY = `cybershield:last-scan:${window.location.href}`;

let currentScanPromise = null;

bootstrap();

function bootstrap() {
  if (window.__cybershieldLoaded) {
    return;
  }

  window.__cybershieldLoaded = true;
  chrome.runtime.onMessage.addListener(handleMessage);
  queueAutoScan();
}

function queueAutoScan() {
  window.setTimeout(() => {
    maybeScanPage('auto').catch((error) => {
      console.debug('CyberShield auto scan skipped:', error.message);
    });
  }, AUTO_SCAN_DELAY_MS);
}

async function handleMessage(message, sender, sendResponse) {
  if (!message) {
    return false;
  }

  if (message.type === 'CYBERSHIELD_PING') {
    sendResponse({ ok: true });
    return false;
  }

  if (message.type === 'CYBERSHIELD_RENDER_RESULT') {
    if (message.result && !message.result.skipped && !message.result.error) {
      renderResult(message.result);
    }
    sendResponse({ ok: true });
    return false;
  }

  if (message.type !== 'CYBERSHIELD_SCAN_PAGE') {
    return false;
  }

  try {
    const result = await maybeScanPage(message.force ? 'manual' : 'auto', message.force);
    sendResponse({ ok: true, result });
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }

  return true;
}

async function maybeScanPage(source, force = false) {
  if (currentScanPromise && !force) {
    return currentScanPromise;
  }

  const scanContext = buildScanContext(force);
  if (!scanContext.shouldScan) {
    const skippedResult = {
      url: window.location.href,
      skipped: true,
      reason: scanContext.skipReason,
      scannedAt: new Date().toISOString(),
      source,
    };

    await persistScan(skippedResult);
    return skippedResult;
  }

  if (!force) {
    const pageScanTime = window.sessionStorage.getItem(PAGE_SCAN_KEY);
    if (pageScanTime && Date.now() - Number(pageScanTime) < SCAN_COOLDOWN_MS) {
      const recentScan = await readLastScan();
      if (recentScan && recentScan.url === window.location.href) {
        renderStoredResult(recentScan);
        return recentScan;
      }
    }

    const recentScan = await readLastScan();
    if (
      recentScan &&
      recentScan.url === window.location.href &&
      recentScan.scannedAt &&
      Date.now() - new Date(recentScan.scannedAt).getTime() < SCAN_COOLDOWN_MS
    ) {
      renderStoredResult(recentScan);
      return recentScan;
    }
  }

  currentScanPromise = scanPage(scanContext, source);

  try {
    return await currentScanPromise;
  } finally {
    currentScanPromise = null;
  }
}

function buildScanContext(force = false) {
  const textContent = (document.body?.innerText || '').trim();

  if (!textContent) {
    return { shouldScan: false, skipReason: 'No readable page text found.' };
  }

  if (force) {
    return {
      shouldScan: true,
      textContent,
    };
  }

  if (textContent.length < AUTO_SCAN_MIN_TEXT_LENGTH) {
    return {
      shouldScan: false,
      skipReason: 'Page does not contain enough readable text to scan yet.',
    };
  }

  return {
    shouldScan: true,
    textContent,
  };
}

async function scanPage(scanContext, source) {
  showScanningBadge();

  try {
    const response = await chrome.runtime.sendMessage({
      type: 'CYBERSHIELD_ANALYZE_PAGE',
      payload: {
        url: window.location.href,
        content: scanContext.textContent,
      },
    });

    if (!response?.ok) {
      throw new Error(response?.error || 'Analyze request failed.');
    }

    const data = response.result;
    const result = {
      ...data,
      url: window.location.href,
      skipped: false,
      scannedAt: new Date().toISOString(),
      source,
    };

    await persistScan(result);
    window.sessionStorage.setItem(PAGE_SCAN_KEY, String(Date.now()));
    renderResult(result);
    return result;
  } catch (error) {
    const failedResult = {
      url: window.location.href,
      skipped: false,
      error: error.message,
      scannedAt: new Date().toISOString(),
      source,
    };

    await persistScan(failedResult);
    showErrorBanner(error.message);
    throw error;
  } finally {
    removeScanningBadge();
  }
}

function renderStoredResult(result) {
  if (!result || result.skipped || result.error) {
    return;
  }

  renderResult(result);
}

function renderResult(data) {
  clearExistingUI();

  if (data.riskLevel === 'HIGH') {
    showWarningOverlay(data);
  } else if (data.riskLevel === 'MEDIUM') {
    showMediumWarningBanner(data);
  } else {
    showSafeBadge(data);
  }
}

function clearExistingUI() {
  document.getElementById('cs-overlay')?.remove();
  document.getElementById('cs-banner')?.remove();
  document.getElementById('cs-safe-badge')?.remove();
  document.getElementById('cs-error-banner')?.remove();
}

function persistScan(result) {
  return chrome.storage.local.set({ [STORAGE_KEY]: result });
}

async function readLastScan() {
  const stored = await chrome.storage.local.get(STORAGE_KEY);
  return stored[STORAGE_KEY] || null;
}

function showWarningOverlay(data) {
  const overlay = document.createElement('div');
  overlay.id = 'cs-overlay';
  overlay.innerHTML = `
    <div style="
      position: fixed; inset: 0; background: rgba(5, 8, 15, 0.92); z-index: 2147483647;
      display: flex; align-items: center; justify-content: center; padding: 20px;
      font-family: Arial, sans-serif;
    ">
      <div style="
        background: #0d1624; color: white; padding: 36px 32px; border-radius: 18px;
        max-width: 560px; width: 100%; text-align: center; border: 2px solid #ff6b6b;
        box-shadow: 0 0 40px rgba(255, 107, 107, 0.35);
      ">
        <div style="font-size: 40px; margin-bottom: 8px;">High Risk Detected</div>
        <div style="
          background: rgba(255, 107, 107, 0.12); border: 1px solid #ff6b6b;
          border-radius: 10px; padding: 10px 16px; margin: 14px 0;
        ">
          <span style="color: #ff6b6b; font-weight: 700; font-size: 18px;">Risk score ${data.score}/100</span>
        </div>
        <p style="color: #d8dee9; font-size: 14px; margin: 12px 0 18px;">${escapeHtml(data.reason)}</p>
        <div style="
          background: #111c2c; border-radius: 10px; padding: 12px; margin: 12px 0;
          font-size: 12px; color: #a9b7c8; text-align: left;
        ">
          <strong style="color: #f7f4ea;">Detected patterns</strong><br/>
          ${(data.patterns || []).map((pattern) => `- ${escapeHtml(pattern)}`).join('<br/>')}
        </div>
        <div style="display: flex; gap: 12px; justify-content: center; margin-top: 22px; flex-wrap: wrap;">
          <button id="cs-proceed"
            style="background: #1f2937; color: #cbd5e1; border: 1px solid #334155;
            padding: 10px 18px; border-radius: 10px; cursor: pointer; font-size: 13px;">
            Proceed anyway
          </button>
          <button id="cs-goback"
            style="background: #ff6b6b; color: white; border: none;
            padding: 10px 22px; border-radius: 10px; cursor: pointer; font-weight: 700; font-size: 14px;">
            Go back
          </button>
        </div>
      </div>
    </div>`;

  document.body.appendChild(overlay);
  document.getElementById('cs-proceed').onclick = () => overlay.remove();
  document.getElementById('cs-goback').onclick = () => history.back();
}

function showMediumWarningBanner(data) {
  const banner = document.createElement('div');
  banner.id = 'cs-banner';
  banner.innerHTML = `
    <div style="
      position: fixed; top: 0; left: 0; width: 100%; z-index: 2147483647;
      background: #f6ad55; color: #1f2937; padding: 12px 18px;
      display: flex; align-items: center; justify-content: space-between; gap: 16px;
      font-family: Arial, sans-serif; font-size: 13px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.28);
    ">
      <span><strong>CyberShield warning:</strong> score ${data.score}/100. ${escapeHtml(data.reason)}</span>
      <button id="cs-close-banner"
        style="background: none; border: none; font-size: 18px; cursor: pointer; color: #1f2937;">x</button>
    </div>`;

  document.body.appendChild(banner);
  document.getElementById('cs-close-banner').onclick = () => banner.remove();
  setTimeout(() => banner.remove(), 8000);
}

function showSafeBadge(data) {
  const badge = document.createElement('div');
  badge.id = 'cs-safe-badge';
  badge.innerHTML = `
    <div style="
      position: fixed; bottom: 20px; right: 20px; z-index: 2147483647;
      background: #1f8f4d; color: white; padding: 10px 14px; border-radius: 999px;
      font-family: Arial, sans-serif; font-size: 12px; box-shadow: 0 2px 12px rgba(31, 143, 77, 0.5);
    ">
      CyberShield: Safe (${data.score}/100)
    </div>`;

  document.body.appendChild(badge);
  setTimeout(() => badge.remove(), 3200);
}

function showScanningBadge() {
  const badge = document.createElement('div');
  badge.id = 'cs-scanning';
  badge.innerHTML = `
    <div style="
      position: fixed; bottom: 20px; right: 20px; z-index: 2147483647;
      background: #101827; color: #7dd3fc; padding: 10px 14px; border-radius: 999px;
      font-family: Arial, sans-serif; font-size: 12px; border: 1px solid rgba(125, 211, 252, 0.35);
    ">
      Scanning page...
    </div>`;

  document.body.appendChild(badge);
}

function showErrorBanner(message) {
  const banner = document.createElement('div');
  banner.id = 'cs-error-banner';
  banner.innerHTML = `
    <div style="
      position: fixed; bottom: 20px; left: 20px; z-index: 2147483647;
      background: #7f1d1d; color: white; padding: 12px 14px; border-radius: 12px;
      font-family: Arial, sans-serif; font-size: 12px; max-width: 360px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.35);
    ">
      CyberShield could not scan this page: ${escapeHtml(message)}
    </div>`;

  document.body.appendChild(banner);
  setTimeout(() => banner.remove(), 5000);
}

function removeScanningBadge() {
  document.getElementById('cs-scanning')?.remove();
}

function escapeHtml(text = '') {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}
