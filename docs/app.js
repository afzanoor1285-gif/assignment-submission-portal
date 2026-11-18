document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('submission-form');
  const alertBox = document.getElementById('alert-box');
  const submissionsBody = document.getElementById('submissions-body');
  const submissionCount = document.getElementById('submission-count');
  const refreshBtn = document.getElementById('refresh-btn');
  const modeBadge = document.getElementById('mode-badge');

  // Determine operational mode: API vs Standalone / Demo (GitHub Pages)
  let isStandaloneDemo = false;
  const LOCAL_STORAGE_KEY = 'portal_submissions_demo';

  // Seed default demo submissions if empty in demo mode
  function getDemoSubmissions() {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) {
      const initial = [
        {
          id: 1,
          name: "Hamza Tariq",
          reg_no: "FA21-BCS-012",
          assignment_title: "DevOps Lab Mid - CI/CD Pipeline",
          submission_url: "https://github.com/hamza/devops-lab",
          submitted_at: new Date(Date.now() - 3600000).toISOString()
        }
      ];
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(initial));
      return initial;
    }
    try {
      return JSON.parse(raw);
    } catch {
      return [];
    }
  }

  function saveDemoSubmission(entry) {
    const list = getDemoSubmissions();
    entry.id = list.length + 1;
    entry.submitted_at = new Date().toISOString();
    list.push(entry);
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(list));
    return entry;
  }

  // URL Validator
  function isValidHttpUrl(string) {
    let url;
    try {
      url = new URL(string);
    } catch (_) {
      return false;
    }
    return url.protocol === "http:" || url.protocol === "https:";
  }

  function showAlert(message, type = 'success') {
    alertBox.textContent = message;
    alertBox.className = `alert alert-${type}`;
    alertBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function clearAlert() {
    alertBox.textContent = '';
    alertBox.className = 'alert hidden';
  }

  function clearFieldErrors() {
    ['name', 'reg_no', 'title', 'url'].forEach(id => {
      const el = document.getElementById(`${id}-error`);
      if (el) el.textContent = '';
    });
    document.querySelectorAll('input').forEach(input => input.classList.remove('is-invalid'));
  }

  function formatDate(isoStr) {
    try {
      const d = new Date(isoStr);
      return d.toLocaleString('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short'
      });
    } catch {
      return isoStr;
    }
  }

  function renderSubmissions(submissions) {
    submissionCount.textContent = submissions.length;
    if (!submissions || submissions.length === 0) {
      submissionsBody.innerHTML = `
        <tr class="empty-row">
          <td colspan="6">No submissions recorded yet. Submit the form to record one.</td>
        </tr>`;
      return;
    }

    submissionsBody.innerHTML = submissions.map((sub, index) => `
      <tr>
        <td><strong>${sub.id || (index + 1)}</strong></td>
        <td>${escapeHtml(sub.name)}</td>
        <td><span class="badge-tag">${escapeHtml(sub.reg_no)}</span></td>
        <td>${escapeHtml(sub.assignment_title)}</td>
        <td>
          <a class="submission-link" href="${escapeHtml(sub.submission_url)}" target="_blank" rel="noopener noreferrer">
            🔗 ${escapeHtml(sub.submission_url)}
          </a>
        </td>
        <td style="color: #718096; font-size: 0.85rem;">${formatDate(sub.submitted_at)}</td>
      </tr>
    `).join('');
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Fetch Submissions
  async function loadSubmissions() {
    if (isStandaloneDemo) {
      renderSubmissions(getDemoSubmissions());
      return;
    }

    try {
      const res = await fetch('/api/submissions');
      if (!res.ok) throw new Error('API server returned error');
      const data = await res.json();
      modeBadge.textContent = 'API Connected';
      modeBadge.className = 'badge badge-success';
      renderSubmissions(data.submissions || []);
    } catch (err) {
      // Switch to standalone demo mode (e.g. on GitHub Pages)
      console.warn('Switching to Standalone Demo Mode (GitHub Pages/Offline)', err);
      isStandaloneDemo = true;
      modeBadge.textContent = 'GitHub Pages Demo Mode';
      modeBadge.className = 'badge badge-info';
      renderSubmissions(getDemoSubmissions());
    }
  }

  // Handle Form Submission
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearAlert();
    clearFieldErrors();

    const name = document.getElementById('name').value.trim();
    const reg_no = document.getElementById('reg_no').value.trim();
    const assignment_title = document.getElementById('assignment_title').value.trim();
    const submission_url = document.getElementById('submission_url').value.trim();

    // Client-side validations
    let hasError = false;

    if (!name) {
      document.getElementById('name-error').textContent = 'Student name is required.';
      document.getElementById('name').classList.add('is-invalid');
      hasError = true;
    }

    if (!reg_no) {
      document.getElementById('reg_no-error').textContent = 'Registration number is required.';
      document.getElementById('reg_no').classList.add('is-invalid');
      hasError = true;
    }

    if (!assignment_title) {
      document.getElementById('title-error').textContent = 'Assignment title is required.';
      document.getElementById('assignment_title').classList.add('is-invalid');
      hasError = true;
    }

    if (!submission_url) {
      document.getElementById('url-error').textContent = 'Submission URL is required.';
      document.getElementById('submission_url').classList.add('is-invalid');
      hasError = true;
    } else if (!isValidHttpUrl(submission_url)) {
      document.getElementById('url-error').textContent = 'Invalid submission URL. Must start with http:// or https://.';
      document.getElementById('submission_url').classList.add('is-invalid');
      hasError = true;
    }

    if (hasError) {
      showAlert('Please correct the validation errors in the form.', 'error');
      return;
    }

    const payload = {
      name,
      reg_no,
      assignment_title,
      submission_url
    };

    // If Standalone Demo Mode (GitHub Pages)
    if (isStandaloneDemo) {
      saveDemoSubmission(payload);
      showAlert(`Assignment "${assignment_title}" submitted successfully (Demo Mode)!`, 'success');
      form.reset();
      renderSubmissions(getDemoSubmissions());
      return;
    }

    // API Mode
    try {
      const res = await fetch('/api/submissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (res.status === 201 && data.success) {
        showAlert(`Assignment "${assignment_title}" submitted and recorded successfully!`, 'success');
        form.reset();
        await loadSubmissions();
      } else {
        const errorMsg = data.error || 'Submission failed. Please check inputs.';
        showAlert(errorMsg, 'error');
        // Map specific error messages to fields
        if (errorMsg.toLowerCase().includes('registration')) {
          document.getElementById('reg_no-error').textContent = errorMsg;
          document.getElementById('reg_no').classList.add('is-invalid');
        } else if (errorMsg.toLowerCase().includes('url')) {
          document.getElementById('url-error').textContent = errorMsg;
          document.getElementById('submission_url').classList.add('is-invalid');
        }
      }
    } catch (err) {
      console.error('API submission failed, falling back to local demo save:', err);
      isStandaloneDemo = true;
      modeBadge.textContent = 'GitHub Pages Demo Mode';
      modeBadge.className = 'badge badge-info';
      saveDemoSubmission(payload);
      showAlert(`Assignment submitted successfully (Demo Mode)!`, 'success');
      form.reset();
      renderSubmissions(getDemoSubmissions());
    }
  });

  refreshBtn.addEventListener('click', () => {
    loadSubmissions();
    showAlert('Submissions list refreshed.', 'success');
    setTimeout(clearAlert, 2000);
  });

  // Initial load
  loadSubmissions();
});
