/**
 * workbook-renderer.js
 * generateWorkbook()이 반환한 데이터를 학생용 워크북 HTML로 변환.
 * 이 HTML을 그대로 브라우저 미리보기에 쓰거나, 백엔드로 보내
 * wkhtmltopdf 등으로 PDF 변환하면 됩니다.
 *
 * 사용 예:
 *   import { renderWorkbookHTML } from "./workbook-renderer.js";
 *   const html = renderWorkbookHTML(workbook, { title: "지문 제목" });
 */

function escapeHtml(str = "") {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ---------------------------------------------------------
// CSS (passage-analysis 스킬과 동일한 색상 팔레트 사용)
// 문법 = 빨강 #C00000, 어휘 = 파랑 #0070C0
// ---------------------------------------------------------
const CSS = `
  @page { size: A4; margin: 18mm 16mm; }
  * { box-sizing: border-box; }
  body {
    font-family: "NanumGothic", "Noto Sans KR", "Malgun Gothic", sans-serif;
    color: #1a1a1a;
    line-height: 1.6;
    font-size: 11pt;
  }
  h1.wb-title { font-size: 18pt; margin: 0 0 4mm; }
  .wb-meta { display:flex; gap: 12mm; font-size: 10pt; color:#555; margin-bottom: 8mm; border-bottom: 1.5px solid #333; padding-bottom: 4mm; }
  .wb-meta span b { color:#111; }

  section.step { page-break-before: always; }
  section.step:first-of-type { page-break-before: auto; }

  .step-header { display:flex; align-items:baseline; gap: 6px; margin-bottom: 6mm; }
  .step-badge {
    display:inline-block; background:#222; color:#fff; font-weight:700;
    font-size: 10pt; padding: 2px 10px; border-radius: 3px;
  }
  .step-title { font-size: 14pt; font-weight:700; }
  .step-desc { font-size: 9.5pt; color:#666; margin-bottom: 6mm; }

  /* Step 1: 해석 */
  .sentence-block { margin-bottom: 6mm; }
  .sentence-en { font-size: 11pt; }
  .sentence-num { color:#0070C0; font-weight:700; margin-right: 4px; }
  .answer-line { border-bottom: 1px solid #999; height: 7mm; margin-top: 2mm; }

  /* Step 2: 빈칸 */
  /* Step 2: 빈칸 (문장별) */
  .step2-block { margin-bottom: 6mm; }
  .step2-en { font-size: 11pt; }
  .blank-fill {
    display:inline-block; min-width: 24mm; border-bottom: 1.5px solid #333;
    margin: 0 2px; height: 1em;
  }
  .step2-ko { font-size: 10pt; color:#666; margin-top: 2mm; }

  /* Step 3: 순서 배열 */
  .order-set { border:1px solid #ccc; border-radius:4px; padding:6mm; margin-bottom:6mm; }
  .order-set h3 { margin:0 0 4mm; font-size:11.5pt; }
  .order-sentence { display:flex; gap:6px; margin-bottom:3mm; align-items:flex-start; }
  .order-box {
    flex:0 0 10mm; height:8mm; border:1.5px solid #333; border-radius:3px;
    display:flex; align-items:center; justify-content:center; font-weight:700;
  }
  .order-label { flex:0 0 6mm; font-weight:700; color:#0070C0; }

  /* Step 4: 언스크램블 */
  .unscramble-item { margin-bottom: 7mm; }
  .unscramble-item .qnum { font-weight:700; color:#0070C0; margin-right:4px; }
  .chunk-row { display:flex; flex-wrap:wrap; gap: 3mm; margin: 3mm 0; }
  .chunk-box {
    border:1.5px solid #333; border-radius:4px; padding: 2mm 4mm;
    font-size: 10.5pt; background:#fff;
  }

  /* 정답지 */
  .answer-key { page-break-before: always; }
  .answer-key h2 { border-bottom: 2px solid #333; padding-bottom:2mm; }
  .answer-key .ak-section { margin-bottom: 8mm; }
  .answer-key .ak-section h3 { font-size:12pt; color:#333; }
  .answer-key ol { padding-left: 18px; }
  .answer-key li { margin-bottom: 2mm; }
`;

// ---------------------------------------------------------
// 1단계 렌더링
// ---------------------------------------------------------
function renderStep1(step1) {
  const items = step1.sentences
    .map(
      (s) => `
      <div class="sentence-block">
        <div class="sentence-en"><span class="sentence-num">${s.id}.</span>${escapeHtml(s.en)}</div>
        <div class="answer-line"></div>
      </div>`
    )
    .join("");

  return `
    <section class="step">
      <div class="step-header"><span class="step-badge">STEP 1</span><span class="step-title">해석하기</span></div>
      <div class="step-desc">각 문장을 읽고 빈 줄에 자연스러운 한글 해석을 쓰세요.</div>
      ${items}
    </section>`;
}

// ---------------------------------------------------------
// 2단계 렌더링
// ---------------------------------------------------------
const BLANK_MARKER = "___BLANK___";

function renderStep2(step1, step2) {
  const kobySentence = {};
  step1.sentences.forEach((s) => (kobySentence[s.id] = s.ko));

  const blocks = step2.sentences
    .map((s) => {
      const parts = s.blanked_en.split(BLANK_MARKER);
      // parts.length - 1 개의 빈칸이 있어야 하고, s.blanks가 그 순서와 매칭됨
      let html = escapeHtml(parts[0]);
      for (let i = 1; i < parts.length; i++) {
        html += `<span class="blank-fill"></span>` + escapeHtml(parts[i]);
      }

      return `
        <div class="step2-block">
          <span class="sentence-num">${s.sentence_id}.</span>
          <span class="step2-en">${html}</span>
          <div class="step2-ko">${escapeHtml(kobySentence[s.sentence_id] || "")}</div>
        </div>`;
    })
    .join("");

  return `
    <section class="step">
      <div class="step-header"><span class="step-badge">STEP 2</span><span class="step-title">빈칸 채우기</span></div>
      <div class="step-desc">한글 해석을 참고해서, 빈칸에 알맞은 영어 단어/표현을 바로 쓰세요.</div>
      ${blocks}
    </section>`;
}

// ---------------------------------------------------------
// 3단계 렌더링
// ---------------------------------------------------------
function renderStep3(step3) {
  const sets = step3.sets
    .map((set) => {
      const rows = set.shuffled_sentences
        .map(
          (s) => `
        <div class="order-sentence">
          <div class="order-label">${s.display_id}</div>
          <div>${escapeHtml(s.text)}</div>
        </div>`
        )
        .join("");

      const orderBoxes = set.shuffled_sentences
        .map(() => `<div class="order-box"></div>`)
        .join("");

      return `
        <div class="order-set">
          <h3>문단 ${set.paragraph_id}</h3>
          ${rows}
          <div style="margin-top:4mm; font-size:10pt; color:#555;">순서 (①→⑥):</div>
          <div style="display:flex; gap:4mm; margin-top:2mm;">${orderBoxes}</div>
        </div>`;
    })
    .join("");

  return `
    <section class="step">
      <div class="step-header"><span class="step-badge">STEP 3</span><span class="step-title">문장 순서 배열</span></div>
      <div class="step-desc">각 문단의 문장을 원래 순서대로 아래 빈칸에 기호(A, B, C...)로 쓰세요.</div>
      ${sets}
    </section>`;
}

// ---------------------------------------------------------
// 4단계 렌더링
// ---------------------------------------------------------
function renderStep4(step4) {
  const items = step4.unscramble
    .map((u) => {
      const chunks = u.shuffled_chunks
        .map((c) => `<div class="chunk-box">${escapeHtml(c)}</div>`)
        .join("");
      return `
        <div class="unscramble-item">
          <div><span class="qnum">${u.sentence_id}.</span>아래 어구를 바르게 배열해서 문장을 완성하세요.</div>
          <div class="chunk-row">${chunks}</div>
          <div class="answer-line"></div>
        </div>`;
    })
    .join("");

  return `
    <section class="step">
      <div class="step-header"><span class="step-badge">STEP 4</span><span class="step-title">어순 배열 (언스크램블)</span></div>
      <div class="step-desc">관사와 명사(구)는 하나의 어구로 묶여 있습니다. 어구를 바르게 배열해서 문장을 완성하세요.</div>
      ${items}
    </section>`;
}

// ---------------------------------------------------------
// 정답지 렌더링 (선택된 단계에 해당하는 섹션만 포함)
// ---------------------------------------------------------
function renderAnswerKey(workbook, steps) {
  const { step1_translation, step2_blanks, step3_ordering, step4_unscramble } = workbook;

  const sections = [];

  if (steps.includes(1) && step1_translation) {
    const step1List = step1_translation.sentences
      .map((s) => `<li>${s.id}. ${escapeHtml(s.ko)}</li>`)
      .join("");
    sections.push(`<div class="ak-section"><h3>STEP 1 해석</h3><ol>${step1List}</ol></div>`);
  }

  if (steps.includes(2) && step2_blanks) {
    const step2List = step2_blanks.sentences
      .filter((s) => s.blanks && s.blanks.length > 0)
      .map((s) => {
        const answers = s.blanks
          .map((b) => `<b>${escapeHtml(b.answer)}</b>`)
          .join(", ");
        return `<li>${s.sentence_id}. ${answers}</li>`;
      })
      .join("");
    sections.push(`<div class="ak-section"><h3>STEP 2 빈칸</h3><ol>${step2List}</ol></div>`);
  }

  if (steps.includes(3) && step3_ordering) {
    const step3List = step3_ordering.sets
      .map((set) => `<li>문단 ${set.paragraph_id}: ${set.correct_order.join(" → ")}</li>`)
      .join("");
    sections.push(`<div class="ak-section"><h3>STEP 3 순서 배열</h3><ol>${step3List}</ol></div>`);
  }

  if (steps.includes(4) && step4_unscramble) {
    const step4List = step4_unscramble.unscramble
      .map((u) => `<li>${u.sentence_id}. ${escapeHtml(u.correct_chunks.join(" "))}</li>`)
      .join("");
    sections.push(`<div class="ak-section"><h3>STEP 4 어순 배열</h3><ol>${step4List}</ol></div>`);
  }

  if (sections.length === 0) return "";

  return `
    <section class="answer-key">
      <h2>정답 (교사용)</h2>
      ${sections.join("\n")}
    </section>`;
}

// ---------------------------------------------------------
// 전체 문서 렌더링
// ---------------------------------------------------------
export function renderWorkbookHTML(workbook, { title = "영어 지문 워크북", includeAnswerKey = true } = {}) {
  // workbook.selectedSteps가 있으면 그걸 따르고, 없으면(과거 데이터 호환) 4단계 전부 표시
  const steps = workbook.selectedSteps || [1, 2, 3, 4];

  const sectionRenderers = {
    1: () => (workbook.step1_translation ? renderStep1(workbook.step1_translation) : ""),
    2: () =>
      workbook.step1_translation && workbook.step2_blanks
        ? renderStep2(workbook.step1_translation, workbook.step2_blanks)
        : "",
    3: () => (workbook.step3_ordering ? renderStep3(workbook.step3_ordering) : ""),
    4: () => (workbook.step4_unscramble ? renderStep4(workbook.step4_unscramble) : ""),
  };

  const body = [
    ...steps.map((n) => sectionRenderers[n] && sectionRenderers[n]()),
    includeAnswerKey ? renderAnswerKey(workbook, steps) : "",
  ]
    .filter(Boolean)
    .join("\n");

  return `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <title>${escapeHtml(title)}</title>
  <style>${CSS}</style>
</head>
<body>
  <h1 class="wb-title">${escapeHtml(title)}</h1>
  <div class="wb-meta">
    <span>이름: <b>______________</b></span>
    <span>날짜: <b>______________</b></span>
  </div>
  ${body}
</body>
</html>`;
}
