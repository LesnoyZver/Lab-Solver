---
name: lab-solver
description: Use when the user sends a file with a lab or practical assignment (coding or theory subjects). Analyzes the task, picks the variant, solves it, fills the report using the subject's template, checks it once and delivers the finished file.
---

# Lab Solver

## User settings
- List number: 5 (change only here)
- Report language: Russian
- Subject templates: `subjects/kpiyap/template.docx` for kpiyap (Конструирование программ и языки программирования) and `subjects/psychology/template.docx` for psychology
- Template for any other subject: `subjects/_default/template.docx`

## Speed rules
- Do each step once. Do not re-read files without need.
- Run the final check (step 5) exactly once against the checklist, no repeat rounds.
- Do not ask questions if the answer can be taken from the assignment or template.

## Report rules (highest priority, override everything else in this file)
1. Task text: copy every task from the assignment exactly, word for word, with the same numbering and order. Do not rephrase, shorten, or add examples, hints, explanations or sample data of your own.
2. No bold text in the report body (task labels, "Код программы:", questions, answers). When copying a paragraph from the template into the body, drop its bold formatting. The title page keeps the template's formatting exactly. Never use bold for emphasis.
3. No comments in code, neither in the report nor in the code you run (//, /* */, #, XML doc comments, docstrings).
4. Code in the report: black text on a white background. No shading, highlight, boxes, dark theme or colored background. Remove any w:shd and highlight from code paragraphs and runs.
5. Work only in Word (.docx): build the file with python-docx or XML editing and check it by extracting its text. Never convert it to PDF or images to check it, never render it. (PNG screenshots of program output are still created to insert into the report.)
6. No conclusions: no "Вывод", "Выводы", "Заключение" or closing summary in any report. If a template has one, delete it from the report.
7. No algorithm: no algorithm description, step lists, flowcharts or explanation of how the program works.
8. Strict template match: the report contains only the elements the template has, in the same order, with the same labels, fonts, sizes, spacing and indents ("Цель работы:", "Задание N.", "Код программы:", "Скрин выполнения программы", "КОНТРОЛЬНЫЕ ВОПРОСЫ:" etc.). Add nothing and remove nothing except what rules 1-7 require. Control questions only if the assignment has them.

## Workflow

### 1. Analyze the assignment
Read the file and note:
- subject, work number and title, teacher
- goal of the work and the list of tasks
- whether there are variants and how many (K)
- formatting requirements, if any
- work type: CODING/TECHNICAL (programming, databases, diagrams) or THEORY/HUMANITIES (psychology, etc.)

If the assignment itself lacks essential data (unclear what to do, no task list), stop and ask the user briefly. Do not invent.
A missing subject folder in `subjects/` is not a reason to stop, see step 4.

### 2. Pick the variant
If the work has variants, compute:

    variant = ((N - 1) mod K) + 1

where N = list number, K = number of variants.
Examples with N = 5: K=3 → variant 2; K=5 → variant 5; K=10 → variant 5; K=4 → variant 1.
State which variant was chosen and how it was computed. If there are no variants, do all tasks.

### 3. Solve
For CODING/TECHNICAL work:
- Complete all tasks of the chosen variant in order.
- Code must run. Run it once and keep the real output for the report.
- Save schemes and diagrams as separate image files.
- Never invent results you did not actually get.

For THEORY/HUMANITIES work (psychology, etc.):
- Answer every task of the chosen variant in order, in academic but plain language, with the depth and length required by the template.
- Base answers on the assignment materials and well-established knowledge. Do not invent sources, quotes, statistics or experiment data.
- If a task needs the student's personal input (own test answers, survey responses, personal observations), insert clearly marked placeholders like [FILL IN: ...] and list them in the final reply.
- Use only references you are sure exist; otherwise omit the references section content and say so.

### 4. Fill the report
- kpiyap (Конструирование программ и языки программирования): use `subjects/kpiyap/template.docx`.
- psychology: use `subjects/psychology/template.docx`.
- any other subject: use `subjects/_default/template.docx`.
- Take structure, headings, style and length from the template.
- In the final reply always state which template was used: the subject's or the general one.
- Fill the title page (subject, work number, title, teacher, variant).
- Sections follow the template.
- Do not change the template's formatting.

### 5. Final check (one pass)
- [ ] variant chosen correctly, tasks belong to this variant
- [ ] all tasks covered, nothing skipped
- [ ] task text matches the assignment word for word
- [ ] coding work: code runs and report output matches the real output
- [ ] theory work: no invented facts, sources or data; placeholders are listed
- [ ] no bold in the body
- [ ] no comments in code
- [ ] no conclusion
- [ ] no algorithm
- [ ] work title, teacher, list number on the title page
- [ ] no template leftovers (`<...>`, "FULL NAME", someone else's data)
- [ ] figure and listing numbering, formatting matches the template

Fix what you find once, then deliver the file. Do not start a second check.

### 6. Reply to the user
Briefly: subject and work, chosen variant, which template was used (subject's or general), path to the finished report, open placeholders or doubts (if any). No retelling of the whole solution.

## Folder structure
lab-solver/
├── SKILL.md
└── subjects/
    ├── _default/
    │   └── template.docx
    ├── kpiyap/
    │   └── template.docx
    └── psychology/
        └── template.docx
