// ============================================================
// verdict.js — 최종 추리 제출 폼 처리
// AI 연동 기능: 사용자가 고른 범인/흉기/동기/추리근거(input)
//              → /api/verdict 호출 → 정답 여부 + AI 피드백(output) 표시
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('verdictForm');
  const reasoning = document.getElementById('reasoning');
  const reasoningCount = document.getElementById('reasoningCount');
  const submitBtn = document.getElementById('submitBtn');
  const submitLabel = document.getElementById('submitLabel');
  const resultBox = document.getElementById('verdictResult');
  const resultTitle = document.getElementById('resultTitle');
  const resultFeedback = document.getElementById('resultFeedback');
  if (!form) return;

  reasoning.addEventListener('input', () => {
    reasoningCount.textContent = `${reasoning.value.length} / 500자`;
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const culprit = form.querySelector('input[name="culprit"]:checked')?.value;
    const weapon = form.weapon.value;
    const motive = form.motive.value;
    const reasoningText = reasoning.value.trim();

    // 실패 처리 기준: 빈 입력(필수값 누락) 검증
    if (!culprit || !weapon || !motive) {
      showResult(false, '입력값을 확인해 주세요', '범인, 흉기, 동기를 모두 선택해야 추리를 제출할 수 있습니다.');
      return;
    }

    submitBtn.disabled = true;
    submitLabel.innerHTML = '<span class="spinner" style="display:inline-block; vertical-align:-2px; margin-right:8px;"></span>AI 수사 지휘관이 채점 중…';

    try {
      const data = await callApi('/api/verdict', { culprit, weapon, motive, reasoning: reasoningText });
      showResult(data.correct, data.correct ? '사건 종결. 당신의 추리가 맞았습니다.' : '아쉽지만, 진범을 놓쳤습니다.', data.feedback);
    } catch (err) {
      // 실패 처리 기준: API 오류(4xx/5xx) 및 응답 지연/타임아웃
      showResult(null, '판정을 불러오지 못했습니다', err.message || '잠시 후 다시 시도해 주세요.');
    } finally {
      submitBtn.disabled = false;
      submitLabel.textContent = '추리 제출하기';
    }
  });

  function showResult(correct, title, feedback) {
    resultBox.classList.remove('win', 'lose');
    resultBox.classList.add('is-visible');
    if (correct === true) resultBox.classList.add('win');
    else if (correct === false) resultBox.classList.add('lose');
    resultTitle.textContent = title;
    resultFeedback.textContent = feedback;
    resultBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
});
