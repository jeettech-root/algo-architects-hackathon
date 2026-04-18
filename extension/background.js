const API_BASE_URL = 'https://cybershield-backend-t7v6.onrender.com';
const PREDICT_URL = `${API_BASE_URL}/predict`;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== 'CYBERSHIELD_ANALYZE_PAGE') {
    return false;
  }

  analyzeCurrentTab(message.payload?.url)
    .then((result) => {
      console.log('[CyberShield] Predict result:', result);
      sendResponse({ ok: true, result });
    })
    .catch((error) => {
      console.error('[CyberShield] Predict error:', error);
      sendResponse({ ok: false, error: error.message || String(error) });
    });

  return true;
});

async function getActiveTabUrl() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs?.[0]?.url || '';
}

async function analyzeCurrentTab(payloadUrl) {
  const url = payloadUrl || (await getActiveTabUrl());
  if (!url) {
    throw new Error('Unable to determine current tab URL');
  }

  const response = await fetch(PREDICT_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Predict request failed with status ${response.status}`);
  }

  const data = await response.json();
  console.log('[CyberShield] /predict response:', data);
  return data;
}
