import streamlit as st
from openai import OpenAI
import os
import json
import sys
from datetime import datetime

# 한글 인코딩 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# 세션 상태 초기화
if 'history' not in st.session_state:
    st.session_state.history = []

st.title("📝 문제 검사기")

# OpenAI API 키 설정
if 'openai_client' not in st.session_state:
    st.session_state.openai_client = None

api_key = st.sidebar.text_input("OpenAI API 키를 입력하세요", type="password", key="api_key_input")

if api_key and st.session_state.openai_client is None:
    try:
        os.environ["OPENAI_API_KEY"] = api_key
        st.session_state.openai_client = OpenAI()
    except Exception as e:
        st.error(f"OpenAI 클라이언트 초기화 중 오류가 발생했습니다: {str(e)}")
        st.session_state.openai_client = None

# 왼쪽 패널에 대화 기록 표시
with st.sidebar:
    st.header("📚 분석 기록")
    if st.session_state.history:
        for idx, record in enumerate(st.session_state.history):
            with st.expander(f"{record['timestamp']} - {record['topic']}", expanded=False):
                st.write("**문제:**")
                st.write(record['question'])
                st.write("**분석 결과:**")
                st.write(record['feedback'])

# 문제 입력 섹션
st.header("문제 입력")
topic = st.text_input("주제를 입력하세요 (쉼표로 구분하여 여러 주제 입력 가능)", 
    placeholder="예: 한국사, 세계사, 문화")

question_text = st.text_area("문제와 선지를 입력하세요", 
    placeholder="""예시:
1. 다음 중 대한민국의 수도는? [3.5점]

① 부산
② 인천
③ 서울
④ 대구
⑤ 대전""",
    height=300)

def get_ai_feedback(question_text: str, topic: str) -> dict:
    if not st.session_state.openai_client:
        return {"error": "OpenAI API 키가 설정되지 않았습니다."}

    # 주제들을 리스트로 변환
    topics = [t.strip() for t in topic.split(",")]
    topics_text = ", ".join(topics)

    prompt = f"""다음은 '{topics_text}' 주제에 대한 객관식 문제입니다. 
문제와 선지들을 분석하고, 문제의 적절성과 각 선지의 타당성을 평가해주세요.

{question_text}

다음 JSON 형식으로 응답해주세요:
{{
    "difficulty": "상/중/하 중 하나",
    "topic_relevance": "주제와의 연관성 분석 (각 주제별로 분석)",
    "clarity": "문제의 명확성 분석",
    "choices_analysis": [
        {{
            "choice_number": "선지 번호",
            "content": "선지 내용",
            "is_correct": true/false,
            "analysis": "이 선지가 정답/오답인 이유 (정답인 경우 왜 정답인지, 오답인 경우 왜 오답인지 명확히 설명)",
            "improvement": "개선 제안 (오답인 선지에 대해서만 개선 방향 제시)"
        }}
    ],
    "overall_feedback": "전체적인 피드백 (정답 선지의 적절성과 오답 선지들의 타당성에 대한 평가)",
    "suggestions": "문제 개선을 위한 제안사항 (정답 선지는 수정하지 말고, 오답 선지들의 개선 방향만 제시)"
}}

주의사항:
1. 정답인 선지는 수정하지 말고, 오답인 선지들에 대해서만 개선 방향을 제시해주세요.
2. 정답 선지가 잘못되었다고 판단하지 마세요. 문제에서 제시한 정답이 정답입니다.
3. 각 선지의 정답/오답 여부를 명확히 판단하고, 그 이유를 상세히 설명해주세요.
4. 각 주제와의 연관성도 개별적으로 분석해주세요."""

    try:
        response = st.session_state.openai_client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "당신은 교육 전문가이자 문제 출제 전문가입니다. 객관식 문제의 품질을 분석하고 개선점을 제시하는 것이 당신의 역할입니다. 반드시 JSON 형식으로 응답해주세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            response_format={ "type": "json_object" }
        )
        
        # JSON 응답 파싱
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError as e:
            return {"error": f"JSON 파싱 중 오류가 발생했습니다: {str(e)}"}
            
    except Exception as e:
        return {"error": f"API 호출 중 오류가 발생했습니다: {str(e)}"}

if st.button("문제 분석하기"):
    if not api_key:
        st.error("OpenAI API 키를 입력해주세요.")
    elif not topic or not question_text:
        st.error("주제와 문제를 모두 입력해주세요.")
    else:
        with st.spinner("AI가 문제를 분석중입니다..."):
            feedback = get_ai_feedback(question_text, topic)
            
            if "error" in feedback:
                st.error(feedback["error"])
            else:
                # 분석 결과를 세션 상태에 저장
                st.session_state.history.append({
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'topic': topic,
                    'question': question_text,
                    'feedback': feedback
                })
                
                # 분석 결과를 팝업으로 표시
                with st.expander("분석 결과 보기", expanded=True):
                    # 난이도 표시
                    difficulty_color = {
                        "상": "🔴",
                        "중": "🟡",
                        "하": "🟢"
                    }
                    st.markdown(f"### 난이도: {difficulty_color[feedback['difficulty']]} {feedback['difficulty']}")
                    
                    # 주제 연관성
                    st.markdown("### 주제 연관성")
                    st.write(feedback["topic_relevance"])
                    
                    # 문제 명확성
                    st.markdown("### 문제 명확성")
                    st.write(feedback["clarity"])
                    
                    # 선지 분석
                    st.markdown("### 선지 분석")
                    for choice in feedback["choices_analysis"]:
                        st.markdown(f"#### 선지 {choice['choice_number']}: {choice['content']}")
                        st.markdown(f"**정답 여부**: {'✅ 정답' if choice['is_correct'] else '❌ 오답'}")
                        st.markdown("**분석**:")
                        st.write(choice["analysis"])
                        if choice["improvement"]:
                            st.markdown("**개선 제안**:")
                            st.write(choice["improvement"])
                        st.markdown("---")
                    
                    # 전체 피드백
                    st.markdown("### 전체 피드백")
                    st.write(feedback["overall_feedback"])
                    
                    # 개선 제안
                    st.markdown("### 개선 제안")
                    st.write(feedback["suggestions"])
