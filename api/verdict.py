# ============================================================
# api/verdict.py
# POST /api/verdict
# 입력  : { culprit, weapon, motive, reasoning }
# 출력  : { correct, feedback }
# 역할  : 사용자의 최종 추리를 서버에 저장된 정답과 대조하고,
#         AI(Groq)가 탐정 지휘관 톤으로 채점 코멘트를 생성한다.
#         Groq 호출이 실패하더라도 기본 판정 결과는 반드시 반환한다(우아한 실패 처리).
# ============================================================

import json
import os
from http.server import BaseHTTPRequestHandler

import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"
REQUEST_TIMEOUT_SEC = 12

# 정답은 서버에만 존재 (git에 올라가도 상관없는 게임 데이터이지만,
# 프론트엔드 코드에는 절대 노출하지 않는다는 원칙을 보여주는 예시)
SOLUTION = {"culprit": "김도윤", "weapon": "부지깽이", "motive": "복수"}

SOLUTION_STORY = (
    "진범은 정원사 김도윤이다. 해고 통보에 앙심을 품은 그는 정원 창고 열쇠로 몰래 "
    "서재에 들어가 벽난로 옆 부지깽이로 한서준을 가격했다. 창가의 진흙 발자국은 "
    "그가 남긴 흔적이며, 위조 감정서와 유언장 초안은 각각 박선희와 강태오를 둘러싼 "
    "별개의 비밀일 뿐 살인과는 무관했다."
)


def _error(res, status, message):
    body = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
    res.send_response(status)
    res.send_header("Content-Type", "application/json; charset=utf-8")
    res.end_headers()
    res.wfile.write(body)


def _respond(res, status, obj):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
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

        culprit = (payload.get("culprit") or "").strip()
        weapon = (payload.get("weapon") or "").strip()
        motive = (payload.get("motive") or "").strip()
        reasoning = (payload.get("reasoning") or "").strip()[:500]

        # 실패 처리 기준: 필수값 누락
        if not culprit or not weapon or not motive:
            return _error(self, 400, "범인, 흉기, 동기를 모두 선택해야 합니다.")

        matched = sum([
            culprit == SOLUTION["culprit"],
            weapon == SOLUTION["weapon"],
            motive == SOLUTION["motive"],
        ])
        correct = matched == 3

        api_key = os.environ.get("GROQ_API_KEY")
        feedback = None

        if api_key:
            system_prompt = (
                "당신은 노련한 수사 지휘관이다. 아마추어 탐정이 제출한 최종 추리를 짧고 "
                "박진감 있는 한국어 3~5문장으로 채점한다. 아래 정보를 참고해 반드시 사건의 "
                "진실을 근거로 설명하고, 플레이어의 추리 근거에 대해서도 한마디 코멘트한다.\n\n"
                f"실제 정답: 범인={SOLUTION['culprit']}, 흉기={SOLUTION['weapon']}, 동기={SOLUTION['motive']}\n"
                f"사건 전말: {SOLUTION_STORY}\n"
                f"플레이어 제출: 범인={culprit}, 흉기={weapon}, 동기={motive}\n"
                f"플레이어 추리 근거: {reasoning or '(작성하지 않음)'}\n"
                f"일치 항목 수(3개 중): {matched}\n"
                f"최종 판정: {'정답' if correct else '오답'}"
            )
            try:
                resp = requests.post(
                    GROQ_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": GROQ_MODEL,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": "채점 코멘트를 작성해줘."},
                        ],
                        "temperature": 0.7,
                        "max_tokens": 260,
                    },
                    timeout=REQUEST_TIMEOUT_SEC,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    feedback = data["choices"][0]["message"]["content"].strip()
            except requests.exceptions.Timeout:
                feedback = None  # 아래 기본 문구로 대체 (타임아웃 시 우아한 실패 처리)
            except requests.exceptions.RequestException:
                feedback = None

        # AI 호출이 실패했거나 키가 없어도 기본 판정 결과는 항상 제공한다
        if not feedback:
            base = "사건 전말: " + SOLUTION_STORY
            feedback = (base if correct else f"{base}\n\n제출하신 조합은 정답과 달랐습니다. 다시 심문해 보세요.")

        return _respond(self, 200, {"correct": correct, "feedback": feedback, "matched": matched})
