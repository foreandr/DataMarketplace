document.addEventListener('DOMContentLoaded', () => {
  const statusEl = document.getElementById('analysisStatus');
  const countEl = document.getElementById('analysisCount');
  const bodyEl = document.getElementById('analysisBody');
  const runBtn = document.getElementById('runAnalysis');
  const clearBtn = document.getElementById('clearAnalysis');
  const exportJsonBtn = document.getElementById('exportJson');
  const exportCsvBtn = document.getElementById('exportCsv');
  const filterWrap = document.getElementById('advancedFilters');
  const addFilterBtn = document.getElementById('addFilter');
  const fieldOptions = Array.isArray(window.ANALYSIS_JOB_FIELDS)
    ? window.ANALYSIS_JOB_FIELDS.slice()
    : [];
  fieldOptions.sort();

  if (!statusEl || !countEl || !bodyEl || !runBtn || !clearBtn) return;

  let lastData = [];

  function setStatus(text, mode) {
    statusEl.textContent = text;
    statusEl.classList.remove('ok', 'running', 'error');
    if (mode) statusEl.classList.add(mode);
  }

  function formatPay(value) {
    if (value === null || value === undefined || value === '') return 'â€”';
    const num = Number(value);
    if (Number.isNaN(num)) return String(value);
    return `$${num.toFixed(2)}/hr`;
  }

  function formatBool(value) {
    if (value === null || value === undefined || value === '') return 'â€”';
    if (typeof value === 'string') {
      const normalized = value.trim().toLowerCase();
      if (normalized === 'true' || normalized === 'yes') return 'Yes';
      if (normalized === 'false' || normalized === 'no') return 'No';
      if (normalized === '1') return 'Yes';
      if (normalized === '0') return 'No';
    }
    return Number(value) ? 'Yes' : 'No';
  }

  function escapeCsv(value) {
    const str = String(value ?? '');
    if (str.includes('"') || str.includes(',') || str.includes('\n')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  }

  function clearTable(message) {
    bodyEl.innerHTML = '';
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 11;
    cell.className = 'analysis-empty';
    cell.textContent = message || 'No results yet.';
    row.appendChild(cell);
    bodyEl.appendChild(row);
  }

  function renderRows(rows) {
    bodyEl.innerHTML = '';
    if (!rows.length) {
      clearTable('No matching jobs.');
      return;
    }
    for (const row of rows) {
      const tr = document.createElement('tr');

      const posted = document.createElement('td');
      posted.textContent = row.posted_date || 'â€”';
      tr.appendChild(posted);

      const title = document.createElement('td');
      title.textContent = row.title || 'â€”';
      tr.appendChild(title);

      const company = document.createElement('td');
      company.textContent = row.company || 'â€”';
      tr.appendChild(company);

      const pay = document.createElement('td');
      pay.textContent = formatPay(row.pay);
      tr.appendChild(pay);

      const workMode = document.createElement('td');
      workMode.textContent = row.work_mode || 'â€”';
      tr.appendChild(workMode);

      const lmia = document.createElement('td');
      lmia.textContent = formatBool(row.is_lmia);
      tr.appendChild(lmia);

      const directApply = document.createElement('td');
      directApply.textContent = formatBool(row.is_direct_apply);
      tr.appendChild(directApply);

      const city = document.createElement('td');
      city.textContent = row.city || 'â€”';
      tr.appendChild(city);

      const state = document.createElement('td');
      state.textContent = row.state || 'â€”';
      tr.appendChild(state);

      const source = document.createElement('td');
      source.textContent = row.source || 'â€”';
      tr.appendChild(source);

      const linkCell = document.createElement('td');
      const link = document.createElement('a');
      link.textContent = 'Open';
      link.href = row.url || '#';
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.className = 'analysis-link';
      linkCell.appendChild(link);
      tr.appendChild(linkCell);

      bodyEl.appendChild(tr);
    }
  }

  function createFilterRow(initial) {
    const row = document.createElement('div');
    row.className = 'filter-row';

    const field = document.createElement('select');
    field.className = 'filter-field';
    for (const f of fieldOptions) {
      const opt = document.createElement('option');
      opt.value = f;
      opt.textContent = f;
      field.appendChild(opt);
    }
    if (initial?.field) field.value = initial.field;

    const op = document.createElement('select');
    op.className = 'filter-op';
    const ops = ['=', '!=', '<', '<=', '>', '>=', 'like', 'in'];
    for (const o of ops) {
      const opt = document.createElement('option');
      opt.value = o;
      opt.textContent = o;
      op.appendChild(opt);
    }
    if (initial?.op) op.value = initial.op;

    const value = document.createElement('input');
    value.type = 'text';
    value.className = 'filter-value';
    value.placeholder = 'value';
    if (initial?.value) value.value = initial.value;

    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'secondary tiny';
    remove.textContent = 'Remove';
    remove.addEventListener('click', () => row.remove());

    row.appendChild(field);
    row.appendChild(op);
    row.appendChild(value);
    row.appendChild(remove);
    return row;
  }

  function initFilters() {
    if (!filterWrap || !addFilterBtn || !fieldOptions.length) return;
    addFilterBtn.addEventListener('click', () => {
      filterWrap.appendChild(createFilterRow());
    });
    filterWrap.appendChild(createFilterRow());
  }

  function buildWhere() {
    if (!filterWrap) return [];
    const rows = filterWrap.querySelectorAll('.filter-row');
    const where = [];
    for (const row of rows) {
      const field = row.querySelector('.filter-field')?.value;
      const op = row.querySelector('.filter-op')?.value;
      let value = row.querySelector('.filter-value')?.value;
      if (!field || !op || value === undefined) continue;
      value = value.trim();
      if (!value) continue;
      if (op === 'in') {
        const values = value.split(',').map(v => v.trim()).filter(Boolean);
        if (!values.length) continue;
        where.push({ field, op, value: values });
      } else if (op === 'like') {
        if (!value.includes('%')) value = `%${value}%`;
        where.push({ field, op, value });
      } else {
        where.push({ field, op, value });
      }
    }
    return where;
  }

  function gatherPayload() {
    const keyword = (document.getElementById('kw')?.value || '').trim();
    const country = (document.getElementById('country')?.value || '').trim();
    const state = (document.getElementById('state')?.value || '').trim();
    const citiesRaw = (document.getElementById('cities')?.value || '').trim();
    const orderDir = (document.getElementById('orderDir')?.value || 'desc').trim();
    const limit = parseInt(document.getElementById('limit')?.value || '200', 10);
    const workMode = (document.getElementById('workMode')?.value || '').trim();

    const cities = citiesRaw
      ? citiesRaw.split(',').map(s => s.trim()).filter(Boolean)
      : [];

    const sources = [];
    if (document.getElementById('srcCraigslist')?.checked) sources.push('craigslist');
    if (document.getElementById('srcJobbank')?.checked) sources.push('jobbank');
    if (document.getElementById('srcWorkbc')?.checked) sources.push('workbc');
    if (document.getElementById('srcSaskjobs')?.checked) sources.push('saskjobs');
    if (document.getElementById('srcEluta')?.checked) sources.push('eluta');

    const where = buildWhere();
    if (workMode) {
      where.push({ field: 'work_mode', op: '=', value: workMode });
    }

    return {
      keyword,
      country,
      state,
      cities,
      sources,
      order_dir: orderDir,
      limit: Number.isNaN(limit) ? 200 : limit,
      offset: 0,
      where,
    };
  }

  async function runAnalysis() {
    const payload = gatherPayload();
    setStatus('Running query...', 'running');
    clearTable('Loading...');
    countEl.textContent = 'Loading...';

    try {
      const resp = await fetch('/analysis/jobs/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const body = await resp.json();
      if (!resp.ok) {
        setStatus(`Error: ${resp.status}`, 'error');
        clearTable(body.error || 'Request failed.');
        countEl.textContent = '0 results';
        return;
      }
      lastData = body.data || [];
      renderRows(lastData);
      const count = body.metadata?.count ?? lastData.length;
      countEl.textContent = `${count} total Â· showing ${lastData.length}`;
      setStatus('Query complete', 'ok');
    } catch (err) {
      setStatus('Network error', 'error');
      clearTable(String(err));
      countEl.textContent = '0 results';
    }
  }

  function exportJson() {
    if (!lastData.length) return;
    const blob = new Blob([JSON.stringify(lastData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'jobs_analysis.json';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function exportCsv() {
    if (!lastData.length) return;
    const headers = [
      'posted_date',
      'title',
      'company',
      'pay',
      'work_mode',
      'is_lmia',
      'is_direct_apply',
      'city',
      'state',
      'country',
      'source',
      'url',
    ];
    const lines = [headers.join(',')];
    for (const row of lastData) {
      const values = headers.map(h => escapeCsv(row[h]));
      lines.push(values.join(','));
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'jobs_analysis.csv';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  runBtn.addEventListener('click', runAnalysis);
  clearBtn.addEventListener('click', () => {
    lastData = [];
    setStatus('Idle');
    clearTable('Run a query to see jobs.');
    countEl.textContent = '0 results';
  });
  exportJsonBtn?.addEventListener('click', exportJson);
  exportCsvBtn?.addEventListener('click', exportCsv);
  initFilters();
});
