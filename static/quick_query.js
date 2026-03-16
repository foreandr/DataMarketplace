document.addEventListener('DOMContentLoaded', () => {
  const statusEl = document.getElementById('status');
  const resultEl = document.getElementById('result');
  const runBtn = document.getElementById('runQuery');
  const clearBtn = document.getElementById('clearQuery');

  if (!runBtn || !clearBtn || !statusEl || !resultEl) return;

  function setStatus(text, isError = false) {
    statusEl.textContent = text;
    statusEl.classList.toggle('error', isError);
  }

  function formatResult(body) {
    if (!body || typeof body !== 'object') return JSON.stringify(body, null, 2);
    if (Array.isArray(body.data)) {
      if (!body.data.length) return '[]';
      return body.data.map(item => JSON.stringify(item, null, 2)).join('\n\n');
    }
    return JSON.stringify(body, null, 2);
  }

  async function runQuery() {
    const cfg = window.quickQueryConfig || {};
    const collection = cfg.collection || '_craigslist_cars';
    const filter = cfg.filter || {};
    const orderBy = cfg.order_by || [];

    setStatus('Running query...');
    resultEl.textContent = 'Loading...';

    try {
      const resp = await fetch(`/v1/collections/${collection}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ select: ['*'], filter, order_by: orderBy, page_number: 1 }),
      });
      const body = await resp.json();
      if (!resp.ok) {
        setStatus(`Error: ${resp.status}`, true);
        resultEl.textContent = formatResult(body);
        return;
      }
      setStatus('Query complete');
      resultEl.textContent = formatResult(body);
    } catch (err) {
      setStatus('Network error', true);
      resultEl.textContent = String(err);
    }
  }

  runBtn.addEventListener('click', runQuery);
  clearBtn.addEventListener('click', () => {
    setStatus('Idle');
    resultEl.textContent = 'No results yet.';
  });
});