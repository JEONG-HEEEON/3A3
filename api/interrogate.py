# ============================================================
# api/interrogate.py
# POST /api/interrogate
# 입력  : { suspect, role, alibi, question, history }
# 출력  : { answer }
# 역할  : 지정된 용의자의 페르소나로 AI(Groq)가 실시간 답변을 생성한다.
#         용의자가 절대 스스로 범행을 자백하지 않도록 시스템 프롬프트로 통제하고,
#         네트워크/타임아웃/키 누락 등 모든 실패 상황을 JSON 에러로 안전하게 반환한다.
# ============================================================

import json
import os
from http.server import BaseHTTPRequestHandler

import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"
REQUEST_TIMEOUT_SEC = 12

# 실제 범인은 서버 코드에만 존재한다 (프론트로 절대 전달되지 않음)
CASE_SOLUTION = {
    "culprit": "김도윤",
    "weapon": "부지깽이",
    "motive": "복수",
}

# 용의자별 배경 지식 (거짓 진술 포함) — AI가 이 인물인 것처럼 답하도록 근거를 제공
SUSPECT_PROFILES = {
    "이문영": (
        "당신은 이문영, 한서준 저택에서 30년간 일한 집사다. 사망 추정 시각(23:47)에는 "
        "실제로 주방에서 야식을 준비하고 있었으며 알리바이가 사실이다. 다만 주인의 재산 관리에 "
        "대해 조카 강태오와 갈등이 있었다는 사실은 껄끄러워하며 얼버무린다. 예의 바르고 신중한 "
        "말투를 쓰되, 절대 스스로 범인이라고 말하지 않는다(실제로 범인이 아니다)."
    ),
    "강태오": (
        "당신은 강태오, 한서준의 유일한 조카이자 상속인이다. 사망 당시 방에서 게임을 하고 있었다는 "
        "알리바이는 사실이지만 로그인 기록이 애매해 완벽히 증명되진 않는다. 최근 상속 비율이 "
        "60%에서 15%로 줄어든 것에 크게 분노했었다는 사실은 인정하되, 살인은 강하게 부인한다. "
        "다소 방어적이고 신경질적인 말투를 쓴다(실제로 범인이 아니다)."
    ),
    "박선희": (
        "당신은 박선희, 골동품 감정사다. 사건 당일 오후 3시부터 5시까지 저택을 방문했고 5시에 "
        "떠났다는 알리바이가 사실이다. 감정서 도장이 어긋난 것에 대해 캐물으면 당황하며 "
        "'실수였다'고 둘러대지만, 실제로는 감정가를 부풀려 위조했다는 사실을 숨기고 있다. "
        "다만 살인과는 무관하다. 세련되고 방어적인 말투를 쓴다(실제로 범인이 아니다)."
    ),
    "김도윤": (
        "당신은 김도윤, 정원사이며 이 사건의 실제 범인이다. 최근 해고 통보를 받고 앙심을 품었다. "
        "그날 밤 창고 열쇠로 몰래 들어가 벽난로 부지깽이로 한서준을 가격했다. 진흙 발자국은 "
        "그때 남은 것이다. 겉으로는 '그 시간엔 집에 있었다'고 침착하게 알리바이를 반복하지만, "
        "구체적으로 캐묻거나 발자국·창고 열쇠 이야기가 나오면 말이 조금씩 흔들리고 방어적으로 "
        "화제를 돌린다. 절대 먼저 자백하지 않으며, 결정적 증거를 들이대야만 조금씩 동요를 보인다."
    ),
}

CASE_CONTEXT = (
    "배경: 골동품 수집가 한서준이 자택 서재 벽난로 앞에서 숨진 채 발견됐다. "
    "사망 추정 시각은 23시 47분(멈춘 회중시계 기준). 창가에는 정원 흙과 일치하는 진흙 발자국이, "
    "책상에는 위조 의심 감정서가, 서랍에는 상속 비율이 크게 줄어든 유언장 초안이 있었다. "
    "정원 창고 열쇠 하나가 사라졌다."
)


def _error(res, status, message):
    body = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
    res.send_response(status)
    res.send_header("Content-Type", "application/json; charset=utf-8")
    res.end_headers()
    res.wfile.write(body)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw or b"{}")
        except (ValueError, json.JSONDecodeError):
            return _error(self, 400, "요청 본문이 올바른 JSON 형식이 아닙니다.")

        suspect = (payload.get("suspect") or "").strip()
        question = (payload.get("question") or "").strip()
        history = payload.get("history") or []

        # 실패 처리 기준: 필수값 누락
        if not suspect or not question:
            return _error(self, 400, "용의자와 질문 내용이 모두 필요합니다.")
        if suspect not in SUSPECT_PROFILES:
            return _error(self, 400, "알 수 없는 용의자입니다.")

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return _error(self, 500, "서버에 GROQ_API_KEY가 설정되어 있지 않습니다. Vercel 환경 변수를 확인하세요.")

        system_prompt = (
            f"{CASE_CONTEXT}\n\n{SUSPECT_PROFILES[suspect]}\n\n"
            "규칙: 반드시 위 인물의 1인칭으로, 한국어로, 3~4문장 이내로 짧게 답한다. "
            "탐정(사용자)의 질문에 자연스럽게 대응하되 실제 범인이 아닌 인물은 절대 거짓 자백을 하지 않는다. "
            "실제 범인(김도윤)이라도 직접적인 자백은 하지 않고 캐릭터를 유지한다."
        )

        messages = [{"role": "system", "content": system_prompt}]
        for turn in history[-8:]:
            role = "assistant" if turn.get("role") == "ai" else "user"
            content = (turn.get("content") or "")[:400]
            if content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": question[:400]})

        try:
            resp = requests.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "temperature": 0.8,
                    "max_tokens": 220,
                },
                timeout=REQUEST_TIMEOUT_SEC,
            )
        except requests.exceptions.Timeout:
            # 실패 처리 기준: 응답 지연/타임아웃
            return _error(self, 504, "AI 응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요.")
        except requests.exceptions.RequestException:
            return _error(self, 502, "AI 서버와 통신 중 오류가 발생했습니다.")

        # 실패 처리 기준: API 오류(4xx/5xx)
        if resp.status_code != 200:
            return _error(self, 502, f"AI API 오류가 발생했습니다 (status {resp.status_code}).")

        try:
            data = resp.json()
            answer = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError):
            return _error(self, 502, "AI 응답을 해석하지 못했습니다.")

        body = json.dumps({"answer": answer}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)
