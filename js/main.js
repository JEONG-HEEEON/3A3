// ============================================================
// main.js — 모든 페이지 공통 스크립트
// (네비게이션 토글 / 손전등 스포트라이트 / 코르크보드 빨간 실 / 진입 애니메이션)
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  initNav();
  initSpotlight();
  initCorkboardString();
  initRevealAnimation();
});

/* 모바일 햄버거 메뉴 */
function initNav() {
  const toggle = document.querySelector('.nav__toggle');
  const links = document.querySelector('.nav__links');
  if (!toggle || !links) return;

  toggle.addEventListener('click', () => {
    links.classList.toggle('is-open');
    const isOpen = links.classList.contains('is-open');
    toggle.setAttribute('aria-expanded', String(isOpen));
  });

  links.querySelectorAll('a').forEach((a) => {
    a.addEventListener('click', () => links.classList.remove('is-open'));
  });
}

/* 마우스를 따라다니는 손전등 불빛 */
function initSpotlight() {
  const spot = document.querySelector('.spotlight');
  if (!spot) return;
  window.addEventListener('pointermove', (e) => {
    spot.style.setProperty('--mx', `${e.clientX}px`);
    spot.style.setProperty('--my', `${e.clientY}px`);
  });
}

/* 코르크보드 안 핀 카드들을 빨간 실로 연결 (SVG 동적 생성) */
function initCorkboardString() {
  const board = document.querySelector('.corkboard');
  if (!board) return;
  const svg = board.querySelector('svg');
  const cards = Array.from(board.querySelectorAll('.pin-card'));
  if (!svg || cards.length < 2) return;

  function draw() {
    const boardRect = board.getBoundingClientRect();
    svg.innerHTML = '';
    for (let i = 0; i < cards.length; i++) {
      const a = cards[i];
      const b = cards[(i + 1) % cards.length];
      const ar = a.getBoundingClientRect();
      const br = b.getBoundingClientRect();
      const x1 = ar.left - boardRect.left + ar.width / 2;
      const y1 = ar.top - boardRect.top + 10;
      const x2 = br.left - boardRect.left + br.width / 2;
      const y2 = br.top - boardRect.top + 10;
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', x1);
      line.setAttribute('y1', y1);
      line.setAttribute('x2', x2);
      line.setAttribute('y2', y2);
      line.setAttribute('stroke', '#a8324a');
      line.setAttribute('stroke-width', '1.5');
      line.setAttribute('opacity', '0.75');
      svg.appendChild(line);
    }
  }
  draw();
  window.addEventListener('resize', draw);
}

/* 스크롤 진입 시 요소들이 살짝 떠오르는 연출 */
function initRevealAnimation() {
  const targets = document.querySelectorAll('[data-reveal]');
  if (!targets.length) return;
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('reveal-up');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });
  targets.forEach((t) => io.observe(t));
}

/* 여러 API 호출 지점에서 재사용하는 공통 fetch 래퍼
   - 실패 처리 기준 3종을 모두 이 함수 하나로 처리한다:
     1) 네트워크/서버 오류(4xx/5xx)  2) 응답 지연(타임아웃)  3) 호출부의 빈 입력 검증은 각 페이지에서 수행 */
async function callApi(url, payload, { timeoutMs = 15000 } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(body.error || `요청이 실패했습니다 (${res.status})`, res.status);
    }
    return await res.json();
  } catch (err) {
    clearTimeout(timer);
    if (err.name === 'AbortError') {
      throw new ApiError('응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요.', 0);
    }
    if (err instanceof ApiError) throw err;
    throw new ApiError('네트워크 오류가 발생했습니다. 연결 상태를 확인해 주세요.', 0);
  }
}

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}
