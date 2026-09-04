const facts = [
  { key: 'website', label: 'Website', initial: 'Next.js', updated: 'Remix' },
  { key: 'database', label: 'Database', initial: 'Postgres', updated: 'Postgres' },
  { key: 'hosting', label: 'Hosting', initial: 'AWS', updated: 'Fly.io' },
  { key: 'timezone', label: 'Timezone', initial: 'Pacific', updated: 'Eastern' },
  { key: 'notifications', label: 'Notifications', initial: 'Slack', updated: 'Teams' },
  { key: 'deploy', label: 'Deploy window', initial: 'Friday', updated: 'Friday' },
];

const systemData = {
  naive: {
    size: 'FULL NOTE', score: '0.999', status: 'PASS', caption: 'The verbatim baseline hands Noah the whole note. Nothing is compressed away, so the update is easy to resolve.',
    context: 'Maya’s launch setup\n\nWebsite: Next.js → Remix\nDatabase: Postgres\nHosting: AWS → Fly.io\nTimezone: Pacific → Eastern\nNotifications: Slack → Teams\nDeploy window: Friday',
    answer: 'The launch runs on Remix with Postgres, hosted on Fly.io. The timezone is Eastern, notifications go to Teams, and the deploy window remains Friday.',
    checks: [['4 updated values landed', 'PASS'], ['2 unchanged values preserved', 'PASS'], ['old values removed', 'PASS']],
  },
  amh: {
    size: '239 chars', score: '0.893', status: 'WARN', caption: 'AMH returns a compact shared-memory view. It keeps the shape of the handoff, but some updated values can be missed.',
    context: 'Maya’s launch setup\n\nWebsite: Remix\nDatabase: Postgres\nHosting: Fly.io\nTimezone: Pacific\nNotifications: Slack\nDeploy window: Friday',
    answer: 'The launch uses Remix and Postgres, runs on Fly.io, and the deploy window is Friday. The timezone and notification channel are unclear.',
    checks: [['2 updated values landed', 'PASS'], ['2 unchanged values preserved', 'PASS'], ['2 updated values missing', 'MISS']],
  },
  mem0: {
    size: '275 chars', score: '0.976', status: 'PASS', caption: 'mem0 extracts a shorter context and still resolves most of the compound update. The trade-off is visible in the missing detail.',
    context: 'Launch project\n\nFramework: Remix\nDB: Postgres\nHost: Fly.io\nTimezone: Eastern\nAlerts: Slack\nDeploy: Friday',
    answer: 'The launch uses Remix with Postgres on Fly.io, in the Eastern timezone. Alerts still go to Slack and deployment is Friday.',
    checks: [['3 updated values landed', 'PASS'], ['2 unchanged values preserved', 'PASS'], ['1 updated value stale', 'MISS']],
  },
};

function renderFacts(targetId, mode) {
  const target = document.getElementById(targetId);
  if (!target) return;
  target.innerHTML = facts.map((fact) => {
    const changed = fact.initial !== fact.updated;
    const value = mode === 'update' ? fact.updated : fact.initial;
    const cls = mode === 'update' && changed ? 'updated' : 'preserved';
    return `<button class="fact ${cls}" data-fact="${fact.label}" data-value="${value}" type="button"><span>${fact.label}</span><span class="value">${value}</span></button>`;
  }).join('');
}

function renderSystem(name) {
  const data = systemData[name];
  document.getElementById('context-size').textContent = data.size;
  document.getElementById('context-paper').textContent = data.context;
  document.getElementById('answer-text').textContent = data.answer;
  document.getElementById('answer-status').textContent = data.status;
  document.getElementById('answer-status').className = `status ${data.status === 'PASS' ? 'pass' : 'warn'}`;
  document.getElementById('score').textContent = data.score;
  document.getElementById('system-caption').textContent = data.caption;
  document.getElementById('checks').innerHTML = data.checks.map(([label, result]) => `<div class="check ${result === 'PASS' ? 'pass' : 'fail'}"><span>${label}</span><b>${result}</b></div>`).join('');
}

renderFacts('facts-initial', 'initial');
renderFacts('facts-update', 'update');
renderSystem('naive');

const toast = document.querySelector('.toast');
let toastTimer;
function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2400);
}
document.querySelectorAll('.fact').forEach((fact) => {
  fact.addEventListener('click', () => {
    const state = fact.classList.contains('updated') ? 'updated by Maya on Thursday' : 'preserved from the original note';
    showToast(`${fact.dataset.fact}: ${fact.dataset.value} · ${state}`);
  });
});

document.querySelectorAll('.system-tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.system-tab').forEach((item) => {
      item.classList.remove('active');
      item.setAttribute('aria-selected', 'false');
    });
    tab.classList.add('active');
    tab.setAttribute('aria-selected', 'true');
    renderSystem(tab.dataset.system);
  });
});

const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
  if (entry.isIntersecting) entry.target.classList.add('visible');
}), { threshold: 0.2 });
document.querySelectorAll('.reveal').forEach((element) => observer.observe(element));

const sections = [...document.querySelectorAll('main section[id]')];
const navLinks = [...document.querySelectorAll('nav a[href^="#"]')];
const navObserver = new IntersectionObserver((entries) => entries.forEach((entry) => {
  if (!entry.isIntersecting) return;
  navLinks.forEach((link) => link.classList.toggle('active', link.getAttribute('href') === `#${entry.target.id}`));
}), { rootMargin: '-35% 0px -55% 0px' });
sections.forEach((section) => navObserver.observe(section));
