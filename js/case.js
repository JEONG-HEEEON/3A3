// ============================================================
// case.js — 증거 상세 모달 + AI 용의자 심문(채팅) 기능
// AI 연동 기능: 사용자가 입력한 질문(input) → /api/interrogate 호출
//              → 용의자 역할의 AI 응답(output)을 채팅 로그에 표시
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  initEvidenceModal();
  initInterrogation();
});

/* ---------------- 증거 상세 모달 ---------------- */
function initEvidenceModal() {
  const modal = document.getElementById('evidenceModal');
  const modalTitle = document.getElementById('modalTitle');
  const modalTag = document.getElementById('modalTag');
  const modalDetail = document.getElementById('modalDetail');
  const closeBtn = document.getElementById('modalClose');
  if (!modal) return;

  document.querySelectorAll('.evidence-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      modalTag.textContent = btn.querySelector('.card__tag').textContent;
      modalTitle.textContent = btn.querySelector('h3').textContent;
      modalDetail.textContent = btn.dataset.detail;
      modal.style.display = 'flex';
    });
  });
  closeBtn.addEventListener('click', () => (modal.style.display = 'none'));
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });
}

/* ---------------- AI 용의자 심문 ---------------- */
function initInterrogation() {
  const suspects = document.querySelectorAll('.suspect');
  const form = document.getElementById('chatForm');
  const input = document.getElementById('chatInput');
  const log = document.getElementById('chatLog');
  const submitBtn = document.getElementById('chatSubmit');
  const nameEl = document.getElementById('activeSuspectName');
  const roleEl = document.getElementById('activeSuspectRole');
  if (!form) return;

  let active = {
    name: suspects[0]?.dataset.name || '이문영',
    role: suspects[0]?.dataset.role || '',
    alibi: suspects[0]?.dataset.alibi || '',
  };
  // 용의자별 대화 기록을 각각 유지 (대화 맥락 전달용)
  const historyBySuspect = {};

  suspects.forEach((btn) => {
    btn.addEventListener('click', () => {
      suspects.forEach((b) => b.classList.remove('is-active'));
      btn.classList.add('is-active');
      active = { name: btn.dataset.name, role: btn.dataset.role, alibi: btn.dataset.alibi };
      nameEl.textContent = active.name;
      roleEl.textContent = active.role;
      log.innerHTML = '';
      appendMsg('system', `${active.name}(${active.role})에 대한 심문을 시작합니다.`);
      (historyBySuspect[active.name] || []).forEach((m) => appendMsg(m.role === 'user' ? 'user' : 'ai', m.content));
    });
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = input.value.trim();

    // 실패 처리 기준 1: 빈 입력(필수값 누락)
    if (!question) {
      appendMsg('error', '질문을 입력해 주세요. 빈 질문은 보낼 수 없습니다.');
      input.focus();
      return;
    }

    appendMsg('user', question);
    input.value = '';
    submitBtn.disabled = true;
    input.disabled = true;
    const typingId = appendTyping();

    historyBySuspect[active.name] = historyBySuspect[active.name] || [];
    historyBySuspect[active.name].push({ role: 'user', content: question });

    try {
      const data = await callApi('/api/interrogate', {
        suspect: active.name,
        role: active.role,
        alibi: active.alibi,
        question,
        history: historyBySuspect[active.name].slice(-8),
      });
      removeTyping(typingId);
      appendMsg('ai', data.answer);
      historyBySuspect[active.name].push({ role: 'ai', content: data.answer });
    } catch (err) {
      removeTyping(typingId);
      // 실패 처리 기준 2, 3: API 오류(4xx/5xx) 및 응답 지연/타임아웃
      appendMsg('error', err.message || '알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.');
    } finally {
      submitBtn.disabled = false;
      input.disabled = false;
      input.focus();
    }
  });

  function appendMsg(type, text) {
    const div = document.createElement('div');
    div.className = `msg msg--${type}`;
    div.textContent = text;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  }

  function appendTyping() {
    const div = document.createElement('div');
    const id = `typing-${Date.now()}`;
    div.id = id;
    div.className = 'msg msg--ai';
    div.innerHTML = '<span class="typing"><span></span><span></span><span></span></span>';
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    return id;
  }
  function removeTyping(id) {
    document.getElementById(id)?.remove();
  }
}
