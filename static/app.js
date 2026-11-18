/**
 * COMSATS University Islamabad (Attock Campus)
 * DevOps Assignment Submission Portal - Client Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('submission-form');
  const alertBox = document.getElementById('alert-box');
  const submissionsBody = document.getElementById('submissions-body');
  const submissionCount = document.getElementById('submission-count');
  const statsTotalCount = document.getElementById('stats-total-count');
  const refreshBtn = document.getElementById('refresh-btn');
  const modeBadge = document.getElementById('mode-badge');
  const modeText = document.getElementById('mode-text');
  const searchInput = document.getElementById('search-input');
  const toastContainer = document.getElementById('toast-container');

  let allSubmissions = [];
  let isStandaloneDemo = false;
  const LOCAL_STORAGE_KEY = 'portal_submissions_demo';

  // Seed default demo submissions if empty on GitHub Pages
  function getDemoSubmissions() {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) {
      const initial = [
        {
          id: 1,
          name: "Afza Noor",
          reg_no: "SP21-BCS-045",
          assignment_title: "DevOps Lab Mid - Automated CI/CD Pipeline",
          submission_url: "https://github.com/afzanoor1285-gif/assignment-submission-portal",
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

  function isValidHttpUrl(string) {
    let url;
    try {
      url = new URL(string);
    } catch (_) {
      return false;
    }
    return url.protocol === "http:" || url.protocol === "https:";
  }

  function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? '✅' : '⚠️';
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(40px)';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
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

  function renderSubmissions(submissions, highlightId = null) {
    const count = submissions ? submissions.length : 0;
    if (submissionCount) submissionCount.textContent = count;
    if (statsTotalCount) statsTotalCount.textContent = count;

    if (!submissions || submissions.length === 0) {
      submissionsBody.innerHTML = `
        <tr class="empty-row">
          <td colspan="6">
            <div class="empty-state">
              <div class="empty-icon">📂</div>
              <p class="empty-title">No submissions match your search</p>
              <p class="empty-sub">Fill out and submit the form above to record your assignment.</p>
            </div>
          </td>
        </tr>`;
      return;
    }

    submissionsBody.innerHTML = submissions.map((sub, index) => {
      const isNew = highlightId && (sub.id === highlightId);
      const rowClass = isNew ? 'new-entry-highlight' : '';
      return `
        <tr class="${rowClass}">
          <td><strong>${sub.id || (index + 1)}</strong></td>
          <td>
            <div class="student-col">
              <span class="student-name">${escapeHtml(sub.name)}</span>
            </div>
          </td>
          <td>
            <span class="reg-badge">${escapeHtml(sub.reg_no)}</span>
          </td>
          <td>
            <span class="assignment-title-cell">${escapeHtml(sub.assignment_title)}</span>
          </td>
          <td>
            <div class="url-action-wrap">
              <a href="${escapeHtml(sub.submission_url)}" target="_blank" rel="noopener noreferrer" class="url-btn" title="Open repository link">
                <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                <span>View Link</span>
              </a>
              <button class="copy-btn" onclick="navigator.clipboard.writeText('${escapeHtml(sub.submission_url)}'); window.showCopiedToast();" title="Copy URL">
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
              </button>
            </div>
          </td>
          <td class="time-cell">
            ${formatDate(sub.submitted_at)}
          </td>
        </tr>
      `;
    }).join('');
  }

  window.showCopiedToast = function() {
    showToast('Submission URL copied to clipboard!', 'success');
  };

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Live filter search
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const term = e.target.value.toLowerCase().trim();
      if (!term) {
        renderSubmissions(allSubmissions);
        return;
      }
      const filtered = allSubmissions.filter(sub => 
        (sub.name && sub.name.toLowerCase().includes(term)) ||
        (sub.reg_no && sub.reg_no.toLowerCase().includes(term)) ||
        (sub.assignment_title && sub.assignment_title.toLowerCase().includes(term))
      );
      renderSubmissions(filtered);
    });
  }

  // Fetch submissions from API or local storage
  async function fetchSubmissions(highlightId = null) {
    if (isStandaloneDemo) {
      allSubmissions = getDemoSubmissions();
      renderSubmissions(allSubmissions, highlightId);
      return;
    }

    try {
      const res = await fetch('/api/submissions');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      allSubmissions = data.submissions || [];
      renderSubmissions(allSubmissions, highlightId);
    } catch (err) {
      console.warn('Backend API unavailable. Falling back to Demo Mode:', err);
      isStandaloneDemo = true;
      if (modeText) modeText.textContent = "Demo / Standalone Mode";
      allSubmissions = getDemoSubmissions();
      renderSubmissions(allSubmissions, highlightId);
    }
  }

  // Detect environment
  async function checkEnvironment() {
    try {
      const res = await fetch('/api/submissions', { method: 'GET' });
      if (res.ok) {
        isStandaloneDemo = false;
        if (modeText) modeText.textContent = "Live Flask API Active";
      } else {
        throw new Error('Not 200 OK');
      }
    } catch {
      isStandaloneDemo = true;
      if (modeText) modeText.textContent = "Interactive Demo (Browser Storage)";
    }
    fetchSubmissions();
  }

  // Form submission handler
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearAlert();
    clearFieldErrors();

    const name = document.getElementById('name').value.trim();
    const reg_no = document.getElementById('reg_no').value.trim();
    const assignment_title = document.getElementById('assignment_title').value.trim();
    const submission_url = document.getElementById('submission_url').value.trim();

    let hasError = false;

    // Client-side validations
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
      document.getElementById('url-error').textContent = 'Invalid submission URL. Must start with http:// or https:// with a valid domain.';
      document.getElementById('submission_url').classList.add('is-invalid');
      hasError = true;
    }

    if (hasError) {
      showAlert('Please correct the validation errors in the form before submitting.', 'error');
      showToast('Form validation failed. Please check required fields.', 'error');
      return;
    }

    const payload = {
      name,
      reg_no,
      assignment_title,
      submission_url
    };

    const submitBtn = document.getElementById('submit-btn');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span>Saving...</span>`;

    try {
      if (isStandaloneDemo) {
        const saved = saveDemoSubmission(payload);
        showAlert(`Assignment "${saved.assignment_title}" recorded successfully for ${saved.name}!`, 'success');
        showToast('Assignment submitted successfully!', 'success');
        form.reset();
        fetchSubmissions(saved.id);
      } else {
        const res = await fetch('/api/submissions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (res.status === 201 && data.success) {
          showAlert(`Assignment "${data.submission.assignment_title}" recorded successfully for ${data.submission.name}!`, 'success');
          showToast('Assignment saved to database!', 'success');
          form.reset();
          fetchSubmissions(data.submission.id);
        } else {
          showAlert(data.error || 'Failed to submit assignment.', 'error');
          showToast(data.error || 'Submission rejected by server.', 'error');
        }
      }
    } catch (err) {
      showAlert(`Network error: ${err.message}`, 'error');
      showToast('Network error while communicating with server.', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  });

  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      fetchSubmissions();
      showToast('Submissions list refreshed', 'success');
    });
  }

  // Initialize
  checkEnvironment();
});
