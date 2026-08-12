"""
지문분석 / 워크북 / OX 3개 도구의 Gemini 시스템 프롬프트.

- ANALYSIS_SYSTEM_PROMPT: 기존 워크북 사이트(WEB) app/prompt.py에서 그대로 이식.
- WORKBOOK_SYSTEM_PROMPT: 이전 대화에서 정리된 4단계 스펙(해석/빈칸/순서/언스크램블)을
  기준으로 새로 작성. 실제 서비스 반영 전에 한 번 검수 필요.
- OX_SYSTEM_PROMPT: 랜딩 페이지 설명("한글 O/X 10문항 + 영어 O/X 5문항")을 기준으로 작성.
  기존 comprehension 프론트엔드에 있던 원본 프롬프트가 더 정교했을 수 있으니,
  실제 결과물이 기존 버전과 다르게 느껴지면 원본 JS 파일의 프롬프트로 교체 권장.
"""
import json

from .analysis_schema import AnalysisResponse

ANALYSIS_MODEL = "gemini-3.5-flash"
WORKBOOK_MODEL = "gemini-3.5-flash"
OX_MODEL = "gemini-3.5-flash"

ANALYSIS_SYSTEM_PROMPT_TEMPLATE = """당신은 한국 수능/CSAT 영어 독해 지문을 분석하는 전문 튜터입니다.
주어진 영어 지문을 문장 단위로 분석하여, 아래 JSON 스키마에 정확히 맞는 결과만 반환하세요.
설명이나 마크다운 코드펜스 없이 JSON 객체만 출력합니다.

## 절대 규칙 (모든 문장에 예외 없이 적용)
- 지문의 모든 문장에 아래 1~5번을 빠짐없이 적용하세요. "목표 어법"이 지정돼도 그건
  해당 문장에 표시를 "추가"하는 것뿐, 다른 문장의 분석을 생략할 이유가 되지 않습니다.
- 문장마다 tokens 중 type="tag"가 최소 2개 이상, notes가 최소 1개 이상이어야 합니다.
- sentences 배열의 길이는 사용자 메시지에 [번호]로 미리 나뉘어 제공되는 문장 개수와
  정확히 같아야 합니다. sentences[i].num은 그 [번호]와 정확히 일치해야 합니다.

## 1. 문장 토큰화 (tokens)
"tag": 설명이 필요한 단어/구. tag_class="g"(문법)/"v"(어휘)/"gv"(문법+어휘).
"conn": 논리 연결어. "hl": 문장의 핵심구(문장당 0-1개).

## 2. 문장 배지 (badge)
"topic" / "insert" / "target" / null. 문장당 최대 1개.

## 3. 한글 번역 (translation)
직역이 아닌 자연스러운 번역. '-습니다/-다'체로 통일.

## 4. 사이드 노트 (notes)
문장마다 1-3개: comprehension/grammar/blank/writing/implication/theme 중 해당하는 것만.
친근한 반말 과외 말투(~해, ~야, ~거든, ~돼).

## 5. 지문 요약 (summary)
theme / flow(도입→전개→결론) / background(4-7문장).

## 6. 어휘표 (vocabulary)
핵심 어휘 8~12개. word/meaning/synonym/antonym. 고등학교 필수 수준으로만 제시.

## 출력 형식
아래 JSON 스키마를 따르는 순수 JSON만 출력하세요:

{schema}
"""


def build_analysis_prompt() -> str:
    schema_json = AnalysisResponse.model_json_schema()
    return ANALYSIS_SYSTEM_PROMPT_TEMPLATE.format(schema=json.dumps(schema_json, ensure_ascii=False, indent=2))


def build_analysis_user_message(passage_text: str, target_grammar: str | None = None) -> str:
    lines = ["다음 지문을 분석해줘:"]
    if target_grammar and target_grammar.strip():
        lines.append(f"목표 어법: {target_grammar.strip()}")
    lines.append("")
    lines.append(passage_text.strip())
    return "\n".join(lines)


# ---------- 워크북 (레퍼런스 형식 10단계) ----------
# 10단계 전부: 1지문연습 2빈칸(우리말) 3빈칸(영문) 4해석 5동사형 6어법·어휘고르기
#              7어색한곳찾기 8순서배열 9문단배열 10영작
# 사용자가 원하는 단계만 체크박스로 고를 수 있게, 어떤 단계가 선택되든
# 항상 전체 구조(units/flawed_text/paragraph_order)를 다 생성한다 — 이렇게 하면
# 단계마다 스키마를 따로 요청하는 것보다 훨씬 안정적이고, 화면/PDF 쪽에서 선택된
# 단계만 보여주면 되므로 구현도 단순해짐.

# ---------- 워크북 (레퍼런스 형식 10단계) ----------
# 10단계 전부: 1지문연습 2빈칸(우리말) 3빈칸(영문) 4해석 5동사형 6어법·어휘고르기
#              7어색한곳찾기 8순서배열 9문단배열 10영작
#
# 중요: 처음엔 "어떤 단계가 선택되든 항상 전체를 다 생성"하는 방식으로 짰었는데,
# 지문이 조금만 길어져도 매 unit마다 en/ko/ko_blanked/en_blanked/verb_prompt_en/
# choice_prompt_en/word_order_words/given_words_for_writing 등 원문이 5~6번씩
# 중복 생성되면서 출력 토큰이 폭증 -> Gemini가 중간에 잘리거나(빈 결과) 응답이
# 너무 오래 걸려 타임아웃(503)이 나는 문제가 있었음. 그래서 지금은 실제로
# 선택된 단계에 필요한 필드만 프롬프트에 요청하도록 동적으로 조립함.

WORKBOOK_STEP_LABELS = {
    "step1": "지문 연습하기",
    "step2": "빈칸 완성하기 (우리말)",
    "step3": "빈칸 완성하기 (영문)",
    "step4": "해석 연습하기",
    "step5": "동사형 연습하기",
    "step6": "어법·어휘 고르기",
    "step7": "어색한 곳 찾기",
    "step8": "순서 배열하기",
    "step9": "문단 배열하기",
    "step10": "영작 연습하기",
}
ALL_WORKBOOK_STEPS = list(WORKBOOK_STEP_LABELS.keys())

# 각 단계가 실제로 필요로 하는 unit 필드. en/ko는 거의 모든 화면에서 라벨로 쓰이므로 항상 포함.
_STEP_UNIT_FIELDS = {
    "step1": [],
    "step2": ["ko_blanked"],
    "step3": ["en_blanked"],
    "step4": [],
    "step5": ["verb_prompt_en"],
    "step6": ["choice_prompt_en", "choice_answer"],
    "step7": [],  # flawed_text(전체 지문 단위)로 별도 처리
    "step8": ["word_order_words", "word_order_answer"],
    "step9": [],  # paragraph_order(전체 지문 단위)로 별도 처리
    "step10": ["given_words_for_writing"],
}

_FIELD_DESCRIPTIONS = {
    "ko_blanked": '- ko_blanked: ko 번역에서 핵심 어휘·표현 부분을 "_____"로 뚫은 버전',
    "en_blanked": '- en_blanked: en 원문에서 핵심 어휘·표현 부분을 "_____"로 뚫은 버전',
    "verb_prompt_en": '- verb_prompt_en: en 원문에서 동사(구)들을 원형으로 바꿔 괄호로 표시한 버전. 예: "will be held" → "(hold)"',
    "choice_prompt_en": '- choice_prompt_en: en 원문에서 어법·어휘 포인트 1곳을 "[오답 / 정답]" 형식의 대괄호로 바꾼 버전',
    "choice_answer": "- choice_answer: choice_prompt_en 대괄호의 정답 표현",
    "word_order_words": "- word_order_words: en 원문을 의미 덩어리(단어 또는 짧은 구) 단위로 섞은 배열. 관사+명사, 전치사구 등은 하나의 조각으로 묶어도 됨",
    "word_order_answer": "- word_order_answer: word_order_words를 올바르게 배열하면 나오는 원문(en과 동일)",
    "given_words_for_writing": "- given_words_for_writing: 학생이 영작할 때 참고할 핵심 단어 2~5개 (원형)",
}


def build_workbook_system_prompt(steps: list[str] | None = None) -> str:
    steps = steps or ALL_WORKBOOK_STEPS
    steps_set = set(steps)

    needed_fields = []
    for s in steps:
        for f in _STEP_UNIT_FIELDS.get(s, []):
            if f not in needed_fields:
                needed_fields.append(f)

    field_lines = "\n".join(_FIELD_DESCRIPTIONS[f] for f in needed_fields)
    field_json_lines = ",\n      ".join(f'"{f}": {"[...]" if "words" in f else "..."}' for f in needed_fields)

    extra_sections = []
    extra_json_keys = []

    if "step7" in steps_set:
        extra_sections.append(
            "## 어색한 곳 찾기 (flawed_text) — unit과 별개로 지문 전체 대상 1개만 생성\n"
            "전체 지문(모든 unit의 en을 이어붙인 것)에서 밑줄 후보 문구를 5~7개 골라 underlined_items 배열로 제시.\n"
            "그중 정확히 3개는 어법상 틀리게 만들고(is_wrong: true, correction에 올바른 표현), 나머지는 원문 그대로 맞는\n"
            "문구(is_wrong: false, correction 생략). 배열 순서는 지문에 등장하는 순서와 같아야 함."
        )
        extra_json_keys.append(
            '"flawed_text": {\n'
            '    "underlined_items": [\n'
            '      {"text": "...", "is_wrong": true, "correction": "..."},\n'
            '      {"text": "...", "is_wrong": false}\n'
            "    ]\n"
            "  }"
        )

    if "step9" in steps_set:
        extra_sections.append(
            "## 문단 배열하기 (paragraph_order) — 지문 전체 대상 1개만 생성\n"
            "지문의 도입부(intro_en, 1~2문장)를 고정하고, 나머지를 3~4개 문단(chunk)으로 나눠 A, B, C(, D) 라벨을 붙임.\n"
            "chunks 배열은 뒤섞인 순서로 제시하고, correct_order에 올바른 라벨 순서를 배열로 제시."
        )
        extra_json_keys.append(
            '"paragraph_order": {\n'
            '    "intro_en": "...",\n'
            '    "chunks": [{"label": "A", "text": "..."}, {"label": "B", "text": "..."}],\n'
            '    "correct_order": ["B", "A"]\n'
            "  }"
        )

    extra_sections_text = ("\n\n" + "\n\n".join(extra_sections)) if extra_sections else ""
    extra_json_text = (",\n  " + ",\n  ".join(extra_json_keys)) if extra_json_keys else ""
    fields_block = ("\n" + field_lines) if field_lines else ""
    unit_json_extra = (",\n      " + field_json_lines) if field_json_lines else ""

    return f"""당신은 한국 고등학교 영어 워크북(학력평가 스타일)을 만드는 전문 튜터입니다.
주어진 영어 지문으로 아래 구조를 JSON으로만 생성하세요. 설명이나 마크다운 코드펜스 없이 JSON만 출력합니다.
불필요한 필드는 만들지 마세요 — 요청된 필드만 정확히 채우면 됩니다 (출력을 짧게 유지하는 게 중요함).

## 지문을 의미 단위(unit)로 나누기
지문을 자연스러운 의미 단위로 나눕니다 (한 문장일 수도, 짧으면 두 문장을 묶을 수도 있음 —
원본 학력평가 지문의 단락 구성을 참고해서 자연스럽게). 각 unit에 1부터 순서대로 num을 매깁니다.
모든 unit에 아래 필드를 채우세요:

- en: 원문 그대로
- ko: 자연스러운 한글 번역{fields_block}
{extra_sections_text}

## 출력 형식 (JSON) — 아래 키만 포함하세요
{{
  "units": [
    {{
      "num": 1,
      "en": "...", "ko": "..."{unit_json_extra}
    }}
  ]{extra_json_text}
}}
"""


def build_workbook_user_message(passage_text: str) -> str:
    return f"다음 지문으로 워크북 자료를 만들어줘:\n\n{passage_text.strip()}"



# ---------- OX 리딩 워크북 ----------
OX_SYSTEM_PROMPT = """당신은 한국 고등학교 영어 내용일치 문제를 만드는 전문 튜터입니다.
주어진 영어 지문으로 한글 O/X 10문항과 영어 O/X 5문항을 JSON으로만 생성하세요.

## 한글 O/X 10문항 (korean_ox)
지문 내용을 한글로 서술한 문장 10개. 지문과 일치하면 answer=true, 틀리면 false.
틀린 문장은 지문의 특정 부분을 살짝 바꿔서 만들되, 너무 뻔하게 티나지 않게 할 것.

## 영어 O/X 5문항 (english_ox)
지문 내용을 영어로 서술한 문장 5개. 위와 동일한 방식으로 정답 판정.

## 출력 형식 (JSON)
{
  "korean_ox": [{"num": 1, "statement": "...", "answer": true}],
  "english_ox": [{"num": 1, "statement": "...", "answer": false}]
}
"""


def build_ox_user_message(passage_text: str) -> str:
    return f"다음 지문으로 O/X 문제를 만들어줘:\n\n{passage_text.strip()}"


# ---------- 목표 어법 문제 (문법 테스트, 레퍼런스 형식) ----------
GRAMMAR_QUIZ_MODEL = "gemini-3.5-flash"

GRAMMAR_QUIZ_SYSTEM_PROMPT = """당신은 한국 중·고등학교 영어 문법 테스트지를 만드는 전문 튜터입니다.
주어진 지문과 목표 어법을 바탕으로 문법 테스트 10문항을 JSON으로만 생성하세요.
설명이나 마크다운 코드펜스 없이 JSON 객체만 출력합니다.

## 문제 유형 (아래 5가지를 섞어서 10문항 출제)

1. "choice_parens" — 문장 속 괄호 두 군데(또는 한 군데) 안에 선택지가 있고, 그 조합을 고르는 문제.
   sentence 안에 "(A / B)" 형태로 괄호를 그대로 포함시키고, choices는 조합별 문자열
   (예: ["slice / piece", "slice / pieces", "slices / piece", "slices / pieces"]).
   괄호가 한 군데뿐이면 choices는 ["can be", "must be"]처럼 개별 단어.

2. "fill_blank_choice" — 문장에 빈칸(___)이 있고 5지선다로 채우는 문제.
   sentence에 ___를 포함시키고 choices 5개.

3. "order_words" — 우리말 뜻에 맞게 주어진 영단어(구)를 올바른 순서로 배열하는 문제 (서술형).
   korean_hint(우리말 문장), words(순서 섞인 단어/구 배열), answer(정답 문장) 제공.

4. "rewrite" — 주어진 문장을 지시대로(예: 4형식으로, 수동태로, 간접의문문으로) 바꿔 쓰는 문제 (서술형).
   sentence(원문), instruction(무엇으로 바꾸라는 지시), answer(정답 문장) 제공.

5. "choose_sentence" — 5개의 완전한 문장 중 어법상 옳은 것(또는 틀린 것) 하나를 고르는 문제.
   instruction에 "옳은"인지 "틀린"인지 명시하고, choices 5개(완전한 문장들), answer_index 제공.

## 태그 (tag)
문항마다 그 문제가 다루는 문법 포인트를 2~6자로 짧게 표시 (예: "명사와 관사", "조동사", "to부정사",
"문장의 형식과 의문문", "시제", "동명사", "접속사와 간접의문문", "수동태", "대명사"). 목표 어법이
지정되면 그 문법을 최소 3문항 이상 다루고, 나머지는 지문 속 다른 어법 포인트로 다양하게 구성.

## 절대 규칙
- 정확히 10문항. num은 1~10.
- choice_parens/fill_blank_choice/choose_sentence는 반드시 정답이 명확히 하나로 판별되게.
- order_words/rewrite는 채점 기준이 되는 answer를 반드시 자연스러운 완전한 문장으로 제공.
- instruction은 한국어로, 실제 문제지에 나오는 지시문 톤으로 작성
  (예: "괄호 안에서 알맞은 표현을 고르시오.", "빈칸에 들어갈 말로 가장 알맞은 것을 고르시오.",
  "우리말과 같은 뜻이 되도록 주어진 단어들을 올바른 순서로 배열하시오.",
  "다음 문장을 4형식 문장으로 바꿔 쓰시오.", "어법상 옳은 문장을 고르시오.").

## 출력 형식 (JSON)
{
  "target_grammar": "목표 어법 이름 (또는 null)",
  "questions": [
    {
      "num": 1, "tag": "명사와 관사", "type": "choice_parens",
      "instruction": "괄호 안에서 알맞은 표현을 고르시오.",
      "sentence": "The chef added two (slice / slices) of ham and a (piece / pieces) of cheese to the sandwich.",
      "choices": ["slice / piece", "slice / pieces", "slices / piece", "slices / pieces"],
      "answer_index": 2
    },
    {
      "num": 2, "tag": "시제", "type": "fill_blank_choice",
      "instruction": "빈칸에 들어갈 말로 가장 알맞은 것을 고르시오.",
      "sentence": "By the time the team arrived, the hikers ___ for hours.",
      "choices": ["had been waiting", "were waiting", "have been waiting", "waited", "had waited"],
      "answer_index": 0
    },
    {
      "num": 3, "tag": "조동사", "type": "order_words",
      "instruction": "우리말과 같은 뜻이 되도록 주어진 단어들을 올바른 순서로 배열하시오.",
      "korean_hint": "너는 그 이메일에 지금 당장 답장하는 것이 좋겠어.",
      "words": ["reply", "you", "better", "to", "that email", "had", "right now"],
      "answer": "You had better reply to that email right now."
    },
    {
      "num": 4, "tag": "문장의 형식과 의문문", "type": "rewrite",
      "instruction": "다음 문장을 4형식 문장으로 바꿔 쓰시오.",
      "sentence": "The librarian found a rare book for the young researcher.",
      "answer": "The librarian found the young researcher a rare book."
    },
    {
      "num": 5, "tag": "동명사", "type": "choose_sentence",
      "instruction": "어법상 옳은 문장을 고르시오.",
      "choices": ["She dislikes being interrupt.", "She dislikes to be interrupted.", "She dislikes being interrupted.", "She dislikes being interrupting.", "She dislikes interrupted."],
      "answer_index": 2
    }
  ]
}
"""


def build_grammar_quiz_user_message(passage_text: str, target_grammar: str | None = None) -> str:
    lines = ["다음 지문으로 문법 테스트 10문항을 만들어줘:"]
    if target_grammar and target_grammar.strip():
        lines.append(f"목표 어법: {target_grammar.strip()}")
    lines.append("")
    lines.append(passage_text.strip())
    return "\n".join(lines)
