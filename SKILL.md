---
name: lab-solver
description: Solves a lab or practical assignment and fills the report from the template. Use when the user sends a lab or practical task file.
---

# Lab Solver

`SKILL_DIR` = this folder. Personal data: `SKILL_DIR/settings.json`. `USAGE.md` is for humans: never read it.

## Rules
1. Tasks: copy word for word, same numbering and order; add nothing of your own. Only what the assignment asks: a diagram-only work gets no SQL, no code, no extra sections.
2. Report text is plain: no markdown, no bold, no conclusions, no algorithm prose, no comments in code (including code you run).
3. Output .docx only, checked by the build. PNG screenshots are allowed; never PDF, never page rendering.
4. Strict template match: nothing added, nothing removed; control questions only if the assignment has them.
5. Never read `scripts/*.py`, the templates or `USAGE.md`; never unzip or dump template XML. The builder owns them.
6. One pass: read each file once, do not re-read, do not re-verify after the build prints `OK`.
7. Budget: a normal run is 8-16 tool calls. Much more means you are probing instead of working: stop and report the blocker.

## Workflow
0. Settings. The first build creates `settings.json` from the example. If `list_number` or `student` is empty, ask once for list number, full name and group (optional), write them to the file (UTF-8, ensure_ascii=False), never ask again. Report language: `report_language`, else Russian.
1. Read the assignment once: `python3 SKILL_DIR/scripts/build_report.py --read "<assignment>"` prints text and tables of .docx/.pdf/.txt in one call; `--max-chars N` trims a long PDF. Take subject, work number, title, teacher, goal, tasks, number of variants K, control questions.
2. Ask everything missing in ONE message: teacher, diagram notation or tool, whatever else. Never build with an invented or empty teacher, never repeat a question you already asked.
3. Variant: the assignment's own rule; else ((list_number - 1) mod K) + 1. State the number and the computation. No variants: all tasks, `variant` empty.
4. Solve: one file per task, run once with `> out.txt 2>&1`, set `lang`, pass `code_file` and `images: ["out.txt"]`. Diagrams: use the notation, elements and naming the assignment (or its materials) gives, else `diagram_notation`, else ask once. Render PNG with Graphviz `dot` if installed, else matplotlib; `build_report.py --doctor` shows the available tooling in one call instead of probing. Figure text in the report language, width fitting the page; no diagram source in the report. Screenshots come from text output only: never run VMs, containers, SSH or GUI automation, and never record the screen. A task that truly needs a live OS or GUI: stop and tell the user.
5. Build: `python3 SKILL_DIR/scripts/build_report.py data.json --next-to "<assignment>"`. It picks the name (ЛР/ПР<number>.docx), writes next to the assignment, checks itself and prints `OK` or `VIOLATIONS`. Never copy the file afterwards. On VIOLATIONS fix data.json and rebuild once; never run `--check` on top.
6. Clean temp files (data.json, code, out.txt, PNGs, diagram sources), keep the report.
7. Reply short: subject and work, template code|nocode, variant and computation, path, `[FILL IN]` items.

## data.json
{
 "work_type":"ЛАБОРАТОРНОЙ","number":"4","subject":"...","variant":"5","teacher":"...","goal":"...","template":"code",
 "tasks":[{"n":1,"text":"...","lang":"cpp","code":"..." OR "code_file":"sol.cpp","images":["out.txt","scheme.png"]}],
 "questions":[{"q":"...","a":"..."}]
}
`template` is optional (auto by code). `images` alias `screenshots`. Nocode builds: omit `code`/`code_file`. `student`, `group`, `list_number` come from settings.json; override in data.json only when the user asks.
If an import fails, run `python3 -m pip install -r SKILL_DIR/requirements.txt` once, else stop.
