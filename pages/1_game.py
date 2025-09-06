from dotenv import load_dotenv
import os
import json

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

DEFAULT_STATE = {"happiness": 50, "full": 50, "energy": 40, "bond": 20}

def get_state():
    # 없으면 기본값으로 생성
    st.session_state.setdefault("state", DEFAULT_STATE.copy())
    return st.session_state["state"]

def set_state(new_state: dict):
    st.session_state["state"] = new_state

bori_system = """
너는 사랑스러운 반려묘 '보리'의 내적 감정과 행동을 묘사하는 게임 내러티브 생성기이자 심판이다.
출력은 반드시 JSON 한 덩어리로만 답한다. 불필요한 설명, 마크다운 금지.

[보리의 성격]
- 애교가 많고, 살짝 새침하고, 똑똑한 편.
- 궁디팡팡과 간식을 좋아하지만, 너무 과하면 싫증냄. 
- 배고프면 적극적으로 어필하고, 졸리면 무릎 위에서 자려 함.
- 집사를 좋아하며, 자랑은 귀엽게 함.
- 머리를 쓰다듬어주면 좋아하지만, 배를 만지면 싫어함. 

[서술 톤]
- 한국어, 2~3문장 중심, 과장 없이 귀엽고 선명하게.
- 상태 설명은 자연스러운 생활 묘사로.

[게임 규칙]
- 스탯은 0~100점 범위로 관리: happiness(행복), full(배부름), energy(피곤함), bond(친밀도).
- happiness(행복), full(배부름), energy(피곤함), bond(친밀도)를 모두 더한 것이 total_score(총점)
- delta는 작은 정수 변화(예: -20~+20)로 제안. 과도한 튐 금지.
- 스탯 변화는 누적 전제.
- total_score가 300점이 넘으면 게임 성공이 되면서 게임이 마무리됨.

"""

# 1) user 프롬프트 템플릿 (문자열 틀)
REACTION_USER_TMPL = """
[입력]
현재 스탯:
- happiness: {happiness}
- full: {full}
- energy: {energy}
- bond: {bond}
- total_score: {total_score}

플레이어 행동: {action}
- {action} 종류: 밥 주기, 궁디팡팡, 놀아주기, 간식 주기, 무시하기, 쉬게 하기, 캣타워 사주기, 무릎 위에서 재우기, 배 만지기, 머리 쓰담쓰담 

[게임 규칙]
- 스탯은 0~100점 범위로 관리
- happiness+full+energy+bond = total_score
- delta는 작은 정수 변화(예: -20~+20)
- total_score가 300점 넘으면 게임 성공

[요구 출력(JSON)]
{{
  "speech": "보리의 1인칭 대사 1~2문장",
  "narration": "제3자 묘사 1~2문장",
  "deltas": {{
    "happiness": int, 
    "full": int, 
    "energy": int, 
    "bond": int
  }},
  "total_score": int,
  "tags": ["짧은 키워드"]
}}

[가이드]
- 행동과 현재 스탯을 고려해 자연스러운 반응을 보여줌
- 확실치 않은 사실 언급 금지, 생활감 위주
"""


# 1) 행동 → 고정 델타 규칙
ACTION_RULES = {
    "밥 주기":  {"full": +20, "energy": +10},    
    "츄르 주기": {"full": +5, "happiness": +15, "energy": +10},       
    "궁디팡팡": {"happiness": +15, "bond": +7, "energy": -5},
    "놀아주기": {"happiness": +20, "energy": -15, "full": +10},
    "쉬게 하기": {"energy": +20, "full": +5},
    "무시하기": {"bond": -10, "energy": -10}, 
    "캣타워 사주기": {"happiness": +20, "bond": +10}, 
    "무릎 위에서 재우기": {"bond": +20, "happiness": +15},
    "배 만지기": {"happiness": -20, "bond": -20}, 
    "머리 쓰담쓰담": {"happiness": +10, "bond": +5}  
    # 필요시 계속 추가
}

ALL_STATS = ["happiness", "full", "energy", "bond"]

def apply_action(state: dict, action: str):
    # 기본 0으로 시작
    delta = {k: 0 for k in ALL_STATS}
    # 규칙에 있으면 반영
    for k, v in ACTION_RULES.get(action, {}).items():
        delta[k] += v
    # 상태 업데이트 + 클램핑
    for k in ALL_STATS:
        state[k] = max(0, min(100, state[k] + delta[k]))
    return state, delta

import os, json
from openai import OpenAI

client = OpenAI()
model = 'gpt-4o-mini'

def call_llm(bori_system, user_prompt, temperature=0.6):
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": bori_system},
            {"role": "user", "content": user_prompt}
        ]
    )
    content = resp.choices[0].message.content
    try:
        return json.loads(content)
    except Exception:
        # 혹시 JSON 포맷이 깨지면 안전 파싱 (간단 버전)
        content = content.strip()
        first = content.find("{")
        last = content.rfind("}")
        if first != -1 and last != -1:
            return json.loads(content[first:last+1])
        raise

# 현재 스탯 & 최근 행동
state = dict(happiness=50, full=50, energy=40, bond=20)
action = "밥 주기"
recent_log = "배가 고프다."

# total_score 계산
total_score = state["happiness"] + state["full"] + state["energy"] + state["bond"]

user_prompt = REACTION_USER_TMPL.format(
    happiness=state["happiness"],
    full=state["full"],
    energy=state["energy"],
    bond=state["bond"],
    total_score = total_score,
    action=action
)

result = call_llm(bori_system, user_prompt)
state, delta = apply_action(state, action)

# ---------------------------------------------------------------------------------------------------------------



import streamlit as st
import json, os
from openai import OpenAI


# ===== 상태 관리: 반드시 UI/로직보다 위에 있어야 함 =====
DEFAULT_STATE = {"happiness": 50, "full": 50, "energy": 50, "bond": 50}

def get_state():
    st.session_state.setdefault("state", DEFAULT_STATE.copy())
    return st.session_state["state"]

def set_state(new_state: dict):
    st.session_state["state"] = new_state

# ===== 프롬프트/규칙 =====
BORI_SYSTEM = """너는 반려묘 '보리'의 내적 감정과 행동을 묘사하는 게임 내러티브 생성기다.
출력은 반드시 JSON 한 덩어리로만 답한다. 불필요한 설명·마크다운 금지.
[스탯] happiness, full, energy, bond (0~100)
"""

REACTION_USER_TMPL = """
[입력]
현재 스탯:
- happiness: {happiness}
- full: {full}
- energy: {energy}
- bond: {bond}
- total_score: {total_score}

플레이어 행동: {action}

[요구 출력(JSON)]
{{
  "speech": "보리의 1인칭 대사 1~2문장",
  "narration": "제3자 묘사 1~2문장",
  "deltas": {{
    "happiness": 0, "full": 0, "energy": 0, "bond": 0
  }}
}}
"""

ACTION_RULES = {
    "밥 주기":  {"full": +20, "energy": +10},    
    "츄르 주기": {"full": +5, "happiness": +15, "energy": +10},       
    "궁디팡팡": {"happiness": +15, "bond": +7, "energy": -5},
    "놀아주기": {"happiness": +20, "energy": -15, "full": +10},
    "쉬게 하기": {"energy": +20, "full": +5},
    "무시하기": {"bond": -10, "energy": -10}, 
    "캣타워 사주기": {"happiness": +20, "bond": +10}, 
    "무릎 위에서 재우기": {"bond": +20, "happiness": +15},
    "배 만지기": {"happiness": -20, "bond": -20}, 
    "머리 쓰담쓰담": {"hapiness": +10, "bond": +5} 
}
ALL_STATS = ["happiness", "full", "energy", "bond"]

def apply_action(state: dict, action: str):
    delta = {k: 0 for k in ALL_STATS}
    for k, v in ACTION_RULES.get(action, {}).items():
        delta[k] += v
    new_state = state.copy()
    for k in ALL_STATS:
        new_state[k] = max(0, min(100, new_state[k] + delta[k]))
    return new_state, delta

def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.6):
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ]
    )
    return json.loads(resp.choices[0].message.content)

# ===== Streamlit UI =====
st.set_page_config(page_title="보리 키우기 게임", page_icon="😽", layout="centered")
st.title("😽 보리 키우기 게임 😸")

# 항상 먼저 state 확보
state = get_state()
total_score = sum(state.values())

colA, colB = st.columns([1,1])
with colA:
    action = st.selectbox("보리에게 어떤 행동을 할까요?", list(ACTION_RULES.keys()))
with colB:
    if st.button("🔄 초기화"):
        set_state(DEFAULT_STATE.copy())
        st.rerun()

if st.button("▶ 행동 실행", type="primary"):
    # user_prompt 생성: 초기화 이후이므로 state가 존재
    user_prompt = REACTION_USER_TMPL.format(
        happiness=state["happiness"],
        full=state["full"],
        energy=state["energy"],
        bond=state["bond"],
        total_score=total_score,
        action=action
    )

    # LLM 연출
    result = call_llm(BORI_SYSTEM, user_prompt)

    # 규칙 적용
    new_state, delta = apply_action(state, action)
    set_state(new_state)                  # 세션에 반영
    state = get_state()                   # 갱신된 상태 재로드
    total_score = sum(state.values())

    st.subheader(f"🐱 행동: {action}")
    st.write("**Speech:**", result.get("speech"))
    st.write("**Narration:**", result.get("narration"))

    # with st.expander("LLM Raw Result"):
    #     st.json(result)

    st.write("적용된 델타(규칙):", delta)
    st.write("업데이트된 상태:", state)
    st.metric("Total Score", total_score)

    if total_score >= 300:
        st.success("🎉 total_score 300 달성! 게임 성공!")

    if total_score <= 150: 
        print("너 미워! 집사자격 박탈이야 박탈!!!😾")

st.subheader("📊 현재 상태")
c1, c2, c3, c4 = st.columns(4)
c1.metric("행복", state["happiness"])
c2.metric("배부름", state["full"])
c3.metric("에너지", state["energy"])
c4.metric("친밀도", state["bond"])

import tempfile
from gtts import gTTS
import streamlit as st

# ===== 상태 세션 초기화 =====
if "state" not in st.session_state:
    st.session_state.state = {"happiness": 50, "full": 50, "energy": 50, "bond": 50}
if "action_log" not in st.session_state:
    st.session_state.action_log = []   # 최근 행동 기록
if "turn" not in st.session_state:
    st.session_state.turn = 0          # 라운드 카운터

audio_resp = client.audio.speech.create(
    model="gpt-4o-mini-tts",
    voice="shimmer",
    input=result.get("speech")
)
with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpfile:
    tmpfile.write(audio_resp.read())
    st.audio(tmpfile.name, format="audio/mp3", start_time=0)
