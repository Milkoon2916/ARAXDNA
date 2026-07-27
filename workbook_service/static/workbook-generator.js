/**
 * workbook-generator.js
 * 지문(passage)을 넣으면 4단계 워크북 데이터를 생성하는 모듈.
 * 브라우저에서 사용자 자신의 Gemini API 키로 직접 호출하는 구조.
 *
 * 사용 예:
 *   import { generateWorkbook, MODEL_OPTIONS } from "./workbook-generator.js";
 *   const workbook = await generateWorkbook({
 *     passage: "...",
 *     apiKey: "AIza...",
 *     model: "gemini-3.6-flash",
 *   });
 */

// ---------------------------------------------------------
// 1. 모델 옵션 (드롭다운 UI에 그대로 사용 가능)
// ---------------------------------------------------------
export const MODEL_OPTIONS = [
  {
    value: "gemini-3.5-flash-lite",
    label: "빠르고 저렴 (3.5 Flash-Lite)",
    description: "대량 생성/속도 우선일 때",
  },
  {
    value: "gemini-3.6-flash",
    label: "균형 (3.6 Flash) - 추천",
    description: "구조화 추출 정확도와 비용의 균형",
  },
  {
    value: "gemini-3.1-pro",
    label: "고품질 (3.1 Pro)",
    description: "어법 포인트 선정처럼 정교한 판단이 필요할 때",
  },
];

const DEFAULT_MODEL = "gemini-3.6-flash";

const API_BASE = "https://generativelanguage.googleapis.com/v1beta/models";

const SYSTEM_INSTRUCTION =
  "당신은 한국 고등학교 영어 내신 교재를 만드는 전문 교사입니다. " +
  "아래 지문을 분석해서 지시된 형식의 JSON으로만 출력하세요. " +
  "설명, 마크다운, 코드블록 없이 순수 JSON만 반환합니다.";

// ---------------------------------------------------------
// 2. 공통 Gemini 호출 함수
// ---------------------------------------------------------
// 429(쿼터 초과)/503(서버 과부하) 응답에서 자동으로 재시도 대기 시간을 뽑아 기다렸다가 재시도한다.
function parseRetryDelayMs(errJson) {
  const details = errJson?.error?.details || [];
  const retryInfo = details.find((d) => String(d["@type"] || "").includes("RetryInfo"));
  const raw = retryInfo?.retryDelay; // 예: "42s"
  if (raw) {
    const secs = parseFloat(String(raw).replace("s", ""));
    if (!Number.isNaN(secs)) return Math.ceil(secs * 1000) + 1000;
  }
  return null;
}

async function callGemini({ apiKey, model, prompt, schema, onStatus, maxRetries = 4 }) {
  const url = `${API_BASE}/${model}:generateContent?key=${apiKey}`;

  const body = {
    system_instruction: { parts: [{ text: SYSTEM_INSTRUCTION }] },
    contents: [{ role: "user", parts: [{ text: prompt }] }],
    generationConfig: {
      responseMimeType: "application/json",
      responseSchema: schema,
      temperature: 0.3,
    },
  };

  let res;
  for (let attempt = 0; ; attempt++) {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (res.ok || (res.status !== 429 && res.status !== 503) || attempt >= maxRetries) break;

    let waitMs = res.status === 429 ? 20000 : 5000;
    try {
      const errJson = await res.clone().json();
      const parsed = parseRetryDelayMs(errJson);
      if (parsed) waitMs = parsed;
    } catch (e) { /* 파싱 실패 시 기본 대기시간 사용 */ }

    if (onStatus) {
      onStatus(
        res.status === 429
          ? `Gemini 요청 한도(429)에 걸렸어요. ${Math.ceil(waitMs / 1000)}초 후 자동 재시도합니다... (${attempt + 1}/${maxRetries})`
          : `Gemini 서버가 잠시 과부하 상태예요(503). ${Math.ceil(waitMs / 1000)}초 후 자동 재시도합니다... (${attempt + 1}/${maxRetries})`
      );
    }
    await new Promise((r) => setTimeout(r, waitMs));
  }

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Gemini API 오류 (${res.status}): ${errText}`);
  }

  const data = await res.json();
  const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!text) {
    throw new Error("Gemini 응답에서 텍스트를 찾을 수 없습니다.");
  }

  try {
    return JSON.parse(text);
  } catch (e) {
    throw new Error(`JSON 파싱 실패: ${e.message}\n원본: ${text.slice(0, 500)}`);
  }
}

// ---------------------------------------------------------
// 4. 1단계: 해석하기
// ---------------------------------------------------------
const STEP1_SCHEMA = {
  type: "OBJECT",
  properties: {
    sentences: {
      type: "ARRAY",
      items: {
        type: "OBJECT",
        properties: {
          id: { type: "INTEGER" },
          en: { type: "STRING" },
          ko: { type: "STRING" },
        },
        propertyOrdering: ["id", "en", "ko"],
      },
    },
  },
  propertyOrdering: ["sentences"],
};

export async function generateStep1({ passage, apiKey, model = DEFAULT_MODEL, onStatus }) {
  const prompt = `
다음 영어 지문을 문장 단위로 분리하고, 각 문장에 대해 자연스러운 한글 해석(직역보다 의역 우선)을 작성하세요.
문장 id는 1부터 순서대로 매기세요. 인용부호나 콜론으로 인한 문장 내 세부 구분은 하나의 문장으로 취급하세요.

[지문]
${passage}
`.trim();

  return callGemini({ apiKey, model, prompt, schema: STEP1_SCHEMA, onStatus });
}

// ---------------------------------------------------------
// 5. 2단계: 어법/어휘 빈칸
// ---------------------------------------------------------
export const BLANK_MARKER = "___BLANK___";

const STEP2_SCHEMA = {
  type: "OBJECT",
  properties: {
    sentences: {
      type: "ARRAY",
      items: {
        type: "OBJECT",
        properties: {
          sentence_id: { type: "INTEGER" },
          blanked_en: { type: "STRING" },
          blanks: {
            type: "ARRAY",
            items: {
              type: "OBJECT",
              properties: {
                answer: { type: "STRING" },
                type: { type: "STRING", enum: ["grammar", "vocab"] },
                grammar_point: { type: "STRING" },
              },
              propertyOrdering: ["answer", "type", "grammar_point"],
            },
          },
        },
        propertyOrdering: ["sentence_id", "blanked_en", "blanks"],
      },
    },
  },
  propertyOrdering: ["sentences"],
};

// 문장 수 대략 세기 (마침표/느낌표/물음표 기준)
function countSentencesRough(passage) {
  const n = (passage.match(/[.!?][")]?(\s|$)/g) || []).length;
  return Math.max(1, n);
}

// 빈칸 개수 = 문장당 최소 5개
const MIN_BLANKS_PER_SENTENCE = 5;

function calcBlankCount(passage) {
  const sentenceCount = countSentencesRough(passage);
  return sentenceCount * MIN_BLANKS_PER_SENTENCE;
}

export async function generateStep2({
  passage,
  apiKey,
  model = DEFAULT_MODEL,
  sentenceMap, // 1단계에서 만든 { id, en } 배열을 넘기면 sentence_id 정합성이 좋아짐
  onStatus,
}) {
  const sentenceCount = sentenceMap ? sentenceMap.length : countSentencesRough(passage);
  const blankCount = sentenceCount * MIN_BLANKS_PER_SENTENCE;
  const grammarCount = Math.round(blankCount * 0.6);
  const vocabCount = blankCount - grammarCount;

  const prompt = `
다음 영어 지문에서 내신 시험에 나올 만한 어법 포인트와 핵심 어휘를 골라 빈칸 문제를 만드세요.

각 문장마다:
1. blanked_en: 그 문장을 원문 그대로 쓰되, 빈칸으로 만들 단어/표현 자리를 정확히 "${BLANK_MARKER}"로 치환하세요. 빈칸이 아닌 나머지 부분은 원문 철자, 대소문자, 띄어쓰기, 문장부호를 한 글자도 바꾸지 말고 그대로 두세요.
2. blanks: blanked_en에 등장하는 "${BLANK_MARKER}" 순서와 정확히 같은 순서로, 각 빈칸에 원래 있었던 단어/표현(answer)과 구분(type), 어법 포인트(grammar_point)를 배열로 나열하세요.

조건:
- 지문은 총 ${sentenceCount}개의 문장으로 이루어져 있습니다. 문장마다 최소 ${MIN_BLANKS_PER_SENTENCE}개의 빈칸이 나오도록, 전체 빈칸 수를 약 ${blankCount}개(어법 포인트 약 ${grammarCount}개, 핵심 어휘 약 ${vocabCount}개)로 만드세요.
- 문장이 짧아서 ${MIN_BLANKS_PER_SENTENCE}개를 채우기 어렵다면 그 문장에서 가능한 한 최대한 많은 단어/표현을 빈칸으로 만드세요 (전치사, 접속사, 관사, 조동사 등도 빈칸 후보로 적극 활용).
- "${BLANK_MARKER}"는 반드시 이 정확한 문자열이어야 하며, blanks 배열의 개수는 blanked_en 안의 "${BLANK_MARKER}" 개수와 정확히 일치해야 합니다.
- type이 "grammar"인 경우 grammar_point에 해당 어법 이름(예: "관계대명사 계속적 용법")을 적으세요. type이 "vocab"이면 grammar_point는 빈 문자열로 두세요.
- sentence_id는 1부터 시작해 지문 순서대로 매기세요.

[지문]
${passage}
`.trim();

  return callGemini({ apiKey, model, prompt, schema: STEP2_SCHEMA, onStatus });
}

// ---------------------------------------------------------
// 6. 3단계: 문단별 문장 순서 배열
// ---------------------------------------------------------
const STEP3_SCHEMA = {
  type: "OBJECT",
  properties: {
    sets: {
      type: "ARRAY",
      items: {
        type: "OBJECT",
        properties: {
          paragraph_id: { type: "INTEGER" },
          correct_order: {
            type: "ARRAY",
            items: { type: "STRING" }, // display_id 순서, 예: ["B","A","C"]
          },
          shuffled_sentences: {
            type: "ARRAY",
            items: {
              type: "OBJECT",
              properties: {
                display_id: { type: "STRING" },
                text: { type: "STRING" },
              },
              propertyOrdering: ["display_id", "text"],
            },
          },
        },
        propertyOrdering: ["paragraph_id", "correct_order", "shuffled_sentences"],
      },
    },
  },
  propertyOrdering: ["sets"],
};

// 문단 분리 + 4문장 미만 문단은 인접 문단과 합치기 (LLM에 맡기지 않고 전처리)
function splitParagraphs(passage) {
  const raw = passage
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);

  const paragraphs = raw.length > 0 ? raw : [passage.trim()];

  const countSentences = (p) =>
    (p.match(/[.!?][")]?(\s|$)/g) || []).length || 1;

  const merged = [];
  for (const p of paragraphs) {
    if (
      merged.length > 0 &&
      countSentences(p) < 4 &&
      countSentences(merged[merged.length - 1]) < 8
    ) {
      merged[merged.length - 1] = merged[merged.length - 1] + " " + p;
    } else {
      merged.push(p);
    }
  }
  // 맨 앞 문단이 짧게 혼자 남은 경우 다음 문단과 합치기
  if (merged.length > 1 && countSentences(merged[0]) < 4) {
    merged[1] = merged[0] + " " + merged[1];
    merged.shift();
  }
  return merged;
}

export async function generateStep3({ passage, apiKey, model = DEFAULT_MODEL, onStatus }) {
  const paragraphs = splitParagraphs(passage);

  const results = await Promise.all(
    paragraphs.map((paragraphText, idx) => {
      const prompt = `
다음은 지문의 한 문단입니다. 이 문단을 문장 단위로 분리한 뒤, 순서를 무작위로 섞어서 제시하세요.
학생은 섞인 문장을 원래 순서대로 재배열하는 문제를 풀게 됩니다.

조건:
- display_id는 A, B, C... 알파벳으로 shuffled_sentences 각 항목에 부여하세요 (섞인 순서 그대로).
- correct_order에는 display_id를 원래(정답) 순서대로 나열하세요.
- 문장이 4개 미만이면 억지로 쪼개지 말고 있는 그대로 사용하세요.

[문단 ${idx + 1}]
${paragraphText}
`.trim();

      return callGemini({
        apiKey,
        model,
        prompt,
        onStatus,
        schema: {
          type: "OBJECT",
          properties: {
            correct_order: { type: "ARRAY", items: { type: "STRING" } },
            shuffled_sentences: {
              type: "ARRAY",
              items: {
                type: "OBJECT",
                properties: {
                  display_id: { type: "STRING" },
                  text: { type: "STRING" },
                },
                propertyOrdering: ["display_id", "text"],
              },
            },
          },
          propertyOrdering: ["correct_order", "shuffled_sentences"],
        },
      }).then((r) => ({ paragraph_id: idx + 1, ...r }));
    })
  );

  return { sets: results };
}

// ---------------------------------------------------------
// 7. 4단계: 언스크램블 (관사+수식어+명사 한 덩어리)
// ---------------------------------------------------------
const STEP4_SCHEMA = {
  type: "OBJECT",
  properties: {
    unscramble: {
      type: "ARRAY",
      items: {
        type: "OBJECT",
        properties: {
          sentence_id: { type: "INTEGER" },
          correct_chunks: { type: "ARRAY", items: { type: "STRING" } },
          shuffled_chunks: { type: "ARRAY", items: { type: "STRING" } },
        },
        propertyOrdering: ["sentence_id", "correct_chunks", "shuffled_chunks"],
      },
    },
  },
  propertyOrdering: ["unscramble"],
};

export async function generateStep4({ passage, apiKey, model = DEFAULT_MODEL, onStatus }) {
  const prompt = `
다음 영어 지문의 모든 문장에 대해 언스크램블(어순 배열) 문제를 만드세요.

청크 분리 규칙:
- 관사(a/an/the)는 뒤에 오는 형용사·명사(구)와 반드시 하나의 청크로 묶습니다 (예: "the beautiful girl"은 한 덩어리이며, 절대 "the" / "beautiful" / "girl"로 따로 쪼개지 않습니다).
- 전치사+명사구도 가능하면 하나의 청크로 묶으세요 (예: "in the morning").
- 조동사+본동사 등 동사구는 분리하지 않습니다.
- 문장당 청크는 최소 3개, 최대 8개가 되도록 조정하세요.
- shuffled_chunks는 correct_chunks를 무작위로 섞은 배열입니다 (섞인 순서가 원래 순서와 완전히 같으면 안 됩니다).
- sentence_id는 지문 순서대로 1부터 매기세요 (문장 하나당 하나의 unscramble 항목).

[지문]
${passage}
`.trim();

  return callGemini({ apiKey, model, prompt, schema: STEP4_SCHEMA, onStatus });
}

// ---------------------------------------------------------
// 8. 전체 워크북 생성 (4단계 한 번에)
// ---------------------------------------------------------
export async function generateWorkbook({ passage, apiKey, model = DEFAULT_MODEL, onProgress }) {
  const report = (step) => onProgress && onProgress(step);
  const statusFor = (step) => (message) => report({ step, status: "retry", message });

  report({ step: 1, status: "start" });
  const step1 = await generateStep1({ passage, apiKey, model, onStatus: statusFor(1) });
  report({ step: 1, status: "done" });

  report({ step: 2, status: "start" });
  const step2 = await generateStep2({
    passage,
    apiKey,
    model,
    sentenceMap: step1.sentences,
    onStatus: statusFor(2),
  });
  report({ step: 2, status: "done" });

  report({ step: 3, status: "start" });
  const step3 = await generateStep3({ passage, apiKey, model, onStatus: statusFor(3) });
  report({ step: 3, status: "done" });

  report({ step: 4, status: "start" });
  const step4 = await generateStep4({ passage, apiKey, model, onStatus: statusFor(4) });
  report({ step: 4, status: "done" });

  return {
    passage,
    model,
    step1_translation: step1,
    step2_blanks: step2,
    step3_ordering: step3,
    step4_unscramble: step4,
  };
}
