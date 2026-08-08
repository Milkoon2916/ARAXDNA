/**
 * EXAM4YOU 10단계 워크북 전용 렌더러 (나눔고딕 적용)
 */
class Exam4YouWorkbookRenderer {
    constructor(containerId, metadata) {
        this.container = document.getElementById(containerId);
        this.metadata = metadata || {
            revision: "2022 개정",
            publisher: "NE능률(오선영)",
            subject: "공통영어2",
            lesson: "Lesson 1"
        };
    }

    // 헤더 HTML 생성
    createHeader(stepTitle) {
        return `
            <div class="workbook-header">
                <div class="header-left">${this.metadata.revision} | ${this.metadata.publisher} ${this.metadata.subject}</div>
                <div class="header-center">${this.metadata.lesson}<br><strong>${stepTitle}</strong></div>
                <div class="header-right">교과서 본문</div>
            </div>
        `;
    }

    // 푸터 HTML 생성
    createFooter(pageNo) {
        return `
            <div class="workbook-footer">
                <span>-${pageNo}-</span>
                <span>EXAM4YOU</span>
            </div>
        `;
    }

    // 전체 10단계 렌더링
    renderAll(workbookData) {
        this.container.innerHTML = "";
        let pageCount = 1;

        // Step 1: 본문 해석지
        this.container.appendChild(this.renderStep1(workbookData, pageCount++));
        // Step 2: 빈칸 연습 (우리말)
        this.container.appendChild(this.renderStep2(workbookData, pageCount++));
        // Step 3: 빈칸 연습 (영문)
        this.container.appendChild(this.renderStep3(workbookData, pageCount++));
        // Step 4: 해석 연습
        this.container.appendChild(this.renderStep4(workbookData, pageCount++));
        // Step 5: 동사형 연습
        this.container.appendChild(this.renderStep5(workbookData, pageCount++));
        // Step 6: 어법 선택형 연습
        this.container.appendChild(this.renderStep6(workbookData, pageCount++));
        // Step 7: 어색한 곳 찾기 연습
        this.container.appendChild(this.renderStep7(workbookData, pageCount++));
        // Step 8: 순서배열 연습
        this.container.appendChild(this.renderStep8(workbookData, pageCount++));
        // Step 9: 영작 연습
        this.container.appendChild(this.renderStep9(workbookData, pageCount++));
        // Step 10: Check 종합점검
        this.container.appendChild(this.renderStep10(workbookData, pageCount++));
        // Answer Key
        this.container.appendChild(this.renderAnswerKey(workbookData, pageCount++));
    }

    // [Step 1] 본문 해석지 (2열 표)
    renderStep1(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";
        
        let rowsHtml = data.sentences.map((s, idx) => `
            <tr>
                <td class="en-cell"><span class="num">${idx + 1}</span> ${s.en}</td>
                <td class="ko-cell">${s.ko}</td>
            </tr>
        `).join("");

        page.innerHTML = `
            ${this.createHeader("본문 해석지 (워크북 1)")}
            <p style="font-size:12px; color:#4a5568;">▶ 영문과 해석을 읽으며 문장의 의미를 파악해 보세요.</p>
            <table class="workbook-table">
                <tbody>${rowsHtml}</tbody>
            </table>
            ${this.createFooter(pageNo)}
        `;
        return page;
    }

    // [Step 2] 빈칸 연습 (우리말)
    renderStep2(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";
        
        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item">
                <p><strong>${idx + 1}.</strong> ${s.en}</p>
                <p style="color:#2d3748;">${s.ko_blank || s.ko}</p>
            </div>
        `).join("");

        page.innerHTML = `
            ${this.createHeader("빈칸 연습(우리말) (워크북 2)")}
            <p style="font-size:12px; color:#4a5568;">▶ 영문을 보고 우리말 해석을 완성하시오.</p>
            ${listHtml}
            ${this.createFooter(pageNo)}
        `;
        return page;
    }

    // [Step 3] 빈칸 연습 (영문)
    renderStep3(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";
        
        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item">
                <p style="color:#2d3748;"><strong>${idx + 1}.</strong> ${s.ko}</p>
                <p>${s.en_blank || s.en}</p>
            </div>
        `).join("");

        page.innerHTML = `
            ${this.createHeader("빈칸 연습(영문) (워크북 3)")}
            <p style="font-size:12px; color:#4a5568;">▶ 우리말 해석을 보고 영문을 완성하시오.</p>
            ${listHtml}
            ${this.createFooter(pageNo)}
        `;
        return page;
    }

    // [Step 4] 해석 연습
    renderStep4(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";

        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item">
                <p><strong>${idx + 1}.</strong> ${s.en}</p>
                <div class="answer-space"></div>
            </div>
        `).join("");

        page.innerHTML = `
            ${this.createHeader("해석 연습 (워크북 4)")}
            <p style="font-size:12px; color:#4a5568;">▶ 영어 문장을 읽고 우리말 해석을 쓰시오.</p>
            ${listHtml}
            ${this.createFooter(pageNo)}
        `;
        return page;
    }

    // [Step 5] 동사형 연습
    renderStep5(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";

        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item">
                <p style="color:#4a5568; font-size:12px;">${idx + 1}. ${s.ko}</p>
                <p>${s.verb_practice || s.en}</p>
            </div>
        `).join("");

        page.innerHTML = `
            ${this.createHeader("동사형 연습 (워크북 5)")}
            <p style="font-size:12px; color:#4a5568;">▶ 괄호 안에 주어진 단어를 알맞게 고쳐 쓰세요.</p>
            ${listHtml}
            ${this.createFooter(pageNo)}
        `;
        return page;
    }

    // [Step 6] 어법 선택형 연습
    renderStep6(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";

        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item">
                <p style="color:#4a5568; font-size:12px;">${idx + 1}. ${s.ko}</p>
                <p>${s.grammar_choice || s.en}</p>
            </div>
        `).join("");

        page.innerHTML = `
            ${this.createHeader("어법 선택형 연습 (워크북 6)")}
            <p style="font-size:12px; color:#4a5568;">▶ 괄호 안에서 어법상 알맞은 것을 골라 보세요.</p>
            ${listHtml}
            ${this.createFooter(pageNo)}
        `;
        return page;
    }

    // [Step 7] 어색한 곳 찾기 연습
    renderStep7(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";

        let paragraphHtml = (data.paragraphs || []).map((p, idx) => `
            <div class="sentence-item" style="margin-bottom:20px;">
                <p><strong>[문맥/어법 어색한 곳 찾기 ${idx + 1}]</strong></p>
                <p style="background:#f7fafc; padding:10px; border:1px solid #e2e8f0;">${p.text}</p>
                <p style="font-size:12px; color:#718096;">(1) ______________ → ______________</p>
                <p style="font-size:12px; color:#718096;">(2) ______________ → ______________</p>
                <p style="font-size:12px; color:#718096;">(3) ______________ → ______________</p>
            </div>
        `).join("");

        page.innerHTML = `
            ${this.createHeader("어색한 곳 찾기 연습 (워크북 7)")}
            <p style="font-size:12px; color:#4a5568;">▶ 다음 글의 밑줄 친 부분 중 어색한 것을 찾아 고쳐 쓰시오.</p>
            ${paragraphHtml}
            ${this.createFooter(pageNo)}
        `;
        return page;
    }

    // [Step 8] 순서배열 연습
    renderStep8(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";

        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item">
                <p><strong>${idx + 1}.</strong> ${s.ko}</p>
                <p style="color:#2b6cb0;">${s.scramble || s.en}</p>
                <div class="answer-space"></div>
            </div>
        `).join("");

        page.innerHTML = `
            ${this.createHeader("순서배열 연습 (워크북 8)")}
            <p style="font-size:12px; color:#4a5568;">▶ 다음 우리말과 같은 뜻이 되도록 주어진 단어 및 어구를 알맞게 배열해 보세요.</p>
            ${listHtml}
            ${this.createFooter(pageNo)}
        `;
        return page;
    }

    // [Step 9] 영작 연습
    renderStep9(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";

        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item">
                <p><strong>${idx + 1}.</strong> ${s.ko}</p>
                <p style="font-size:12px; color:#718096;">[제시어]: ${(s.keywords || []).join(", ")}</p>
                <div class="answer-space"></div>
            </div>
        `).join("");

        page.innerHTML = `
            ${this.createHeader("영작 연습 (워크북 9)")}
            <p style="font-size:12px; color:#4a5568;">▶ 다음 우리말과 같은 뜻이 되도록 주어진 단어를 순서대로 사용하여 영작해 보세요.</p>
            ${listHtml}
            ${this.createFooter(pageNo)}
        `;
        return page;
    }

    // [Step 10] Check 종합점검
    renderStep10(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";

        let listHtml = data.sentences.map((s, idx) => `
            <div class="sentence-item">
                <p><span class="num">${idx + 1}</span> ${s.check_item || s.grammar_choice || s.en}</p>
                <p style="font-size:12px; color:#4a5568; text-align:right;">${s.ko}</p>
            </div>
        `).join("");

        page.innerHTML = `
            ${this.createHeader("Check 종합점검 (워크북 10)")}
            <p style="font-size:12px; color:#4a5568;">▶ 어법&어휘 / 영작 / 빈칸 / 순서배열 종합 문제</p>
            ${listHtml}
            ${this.createFooter(pageNo)}
        `;
        return page;
    }

    // Answer Key
    renderAnswerKey(data, pageNo) {
        const page = document.createElement("div");
        page.className = "workbook-page";

        let answersHtml = data.sentences.map((s, idx) => `
            <p style="font-size:12px; margin-bottom:4px;">
                <strong>${idx + 1})</strong> ${s.en} / ${s.ko}
            </p>
        `).join("");

        page.innerHTML = `
            ${this.createHeader("Answer Key")}
            <h3 style="text-align:center; margin-bottom:15px;">정답지 (Answer Key)</h3>
            <div style="column-count: 2; column-gap: 20px;">
                ${answersHtml}
            </div>
            ${this.createFooter(pageNo)}
        `;
        return page;
    }
}
