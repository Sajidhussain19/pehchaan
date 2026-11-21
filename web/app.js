/*
  web/app.js — everything the demo page does (Module 10). Plain JavaScript, no framework.

  WHAT: - loads contact books, demo clips, reminders and the scoreboard from our own API
        - three ways in: a demo clip (with play button), the live mic (MediaRecorder, max 15 s), or typed text
        - shows the strong AI and Pehchaan side by side, with highlighted names, reasons, timings, cost,
          and (for test-set clips) a verdict in WORDS from the same scoring code as the evaluation
        - the clarify panel ("Use this time" / "Always use for 'my doctor'") and the saved reminders
        - "Demo mode": the doctor story in steps, one Next click per step
  WHY:  It is the demo. Every error is shown on screen (no silent failures), and the page never sees the
        OpenAI key: it only calls /api on the same server.

  Safety note: transcripts come from users, so they are always inserted as TEXT (textContent), never as HTML.
*/

"use strict";

// ---------- small helpers ----------
const $ = (sel) => document.querySelector(sel);

/** Build an element: el("p", {class: "x"}, "text", childEl). Strings become text nodes (never HTML). */
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

/** Replace a node's content, skipping empty children (replaceChildren would print "null"). */
function fill(node, ...children) {
  node.replaceChildren(...children.flat().filter((c) => c !== null && c !== undefined && c !== false));
  return node;
}

const state = {
  book: "default",
  compare: true,
  variant: "clean",
  demoKey: null,
  lastReminderId: null,
  config: null,
  busy: false,
};

const RESOLUTION_WORDS = {
  auto: "auto",
  clarified_this_time: "clarified this time",
  clarified_always: "clarified, always",
  preference: "learned preference",
};

function showBanner(message, kind = "error") {
  $("#banner-text").textContent = message;
  $("#banner").className = "banner" + (kind === "info" ? " info" : "");
  $("#banner").setAttribute("role", kind === "info" ? "status" : "alert");
  $("#banner").hidden = false;
}
function hideBanner() { $("#banner").hidden = true; }
$(".banner-close").addEventListener("click", hideBanner);

/** Call our API. Adds the demo key if we have one. Throws an Error with the server's message. */
async function api(path, options = {}) {
  const headers = Object.assign({}, options.headers || {});
  if (state.demoKey) headers["X-Demo-Key"] = state.demoKey;
  let response;
  try {
    response = await fetch(path, Object.assign({}, options, { headers }));
  } catch (err) {
    throw new Error("Can't reach the Pehchaan server. Is it running? (" + err.message + ")");
  }
  let body = null;
  try { body = await response.json(); } catch (_) { /* not JSON */ }
  if (response.status === 401) {
    askForKey();
  }
  if (!response.ok) {
    let detail = body && body.detail;
    if (Array.isArray(detail)) detail = detail.map((d) => d.msg).join("; ");  // validation errors
    throw new Error(detail || `The server answered ${response.status} ${response.statusText}`);
  }
  return body;
}

const ms = (x) => (x === null || x === undefined ? "–" : x >= 1000 ? (x / 1000).toFixed(1) + " s" : Math.round(x) + " ms");
const usd = (x) => (x ? "$" + x.toFixed(5) : "$0");
const fmtTime = (t) => t || null;

// ---------- demo key ----------
function askForKey() {
  const dlg = $("#key-dialog");
  if (!dlg.open) dlg.showModal();
}
$("#key-form").addEventListener("submit", () => {
  state.demoKey = $("#key-input").value.trim();
  try { sessionStorage.setItem("pehchaan-demo-key", state.demoKey); } catch (_) { /* storage blocked: fine */ }
  showBanner("Demo key saved for this tab. Please try again.", "info");
});

// ---------- books ----------
const BOOK_LABELS = {
  default: "Full contacts (evaluated)",
  A: "A: one doctor",
  B: "B: two doctors, no default",
};
let bookDescriptions = {};

async function loadBooks() {
  const books = await api("/api/books");
  const select = $("#book");
  fill(select, ...books.map((b) => el("option", { value: b.book }, BOOK_LABELS[b.book] || b.book)));
  bookDescriptions = Object.fromEntries(books.map((b) => [b.book, b.description]));
  setBook(state.book);
}
function setBook(book) {
  state.book = book;
  $("#book").value = book;
  $("#book-help").textContent = "Contact book: " + (bookDescriptions[book] || book);
}
$("#book").addEventListener("change", (e) => setBook(e.target.value));
$("#compare").addEventListener("change", (e) => { state.compare = e.target.checked; });

// ---------- tabs ----------
document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
  $("#view-demo").hidden = tab.dataset.view !== "demo";
  $("#view-score").hidden = tab.dataset.view !== "score";
  if (tab.dataset.view === "score") loadScoreboard().catch((e) => showBanner(e.message));
}));

// ---------- clips ----------
document.querySelectorAll(".seg-btn").forEach((b) => b.addEventListener("click", () => {
  state.variant = b.dataset.variant;
  document.querySelectorAll(".seg-btn").forEach((x) => x.classList.toggle("active", x === b));
}));

let player = null;
function play(url, button) {
  if (player) { player.pause(); }
  player = new Audio(url);
  button.textContent = "■ Stop";
  player.addEventListener("ended", () => { button.textContent = "▶ Play"; });
  player.addEventListener("error", () => { button.textContent = "▶ Play"; showBanner("Could not play this audio file."); });
  button.onclick = () => { player.pause(); button.textContent = "▶ Play"; button.onclick = () => play(url, button); };
  player.play().catch((e) => showBanner("Could not play audio: " + e.message));
}

async function loadClips() {
  const clips = await api("/api/clips");
  const list = $("#clips");
  let lastGroup = null;
  fill(list, ...clips.flatMap((c) => {
    // A heading whenever the group changes: rehearsed (seen) clips, test-2 clips, dev clips.
    const heading = c.group !== lastGroup ? el("li", { class: "clip-group" }, c.group) : null;
    lastGroup = c.group;
    const kind = c.label || c.demo_kind || c.category;
    const variant = () => (c.audio[state.variant] ? state.variant : Object.keys(c.audio)[0]);
    const playBtn = el("button", { class: "icon-btn", type: "button", "aria-label": `Play clip ${c.clip_id}` }, "▶ Play");
    playBtn.onclick = () => play(c.audio[variant()], playBtn);
    return [heading, el("li", { class: "clip", "data-clip": c.clip_id },
      el("span", { class: "clip-kind" + (c.honest_failure ? " fail" : c.fixed_in_v2 ? " fixed" : "") }, `${c.clip_id} · ${kind}`),
      el("span", { class: "clip-actions" },
        playBtn,
        el("button", { class: "icon-btn clip-run", type: "button", onclick: () => runClip(c.clip_id, variant()) }, "Run")),
      el("span", { class: "clip-text" }, c.text))];
  }));
}

// ---------- the three inputs ----------
async function runClip(clipId, variant) {
  document.querySelectorAll(".clip").forEach((li) => li.classList.toggle("selected", li.dataset.clip === clipId));
  if (state.book !== "default") {
    setBook("default");
    showBanner("Demo clips use the full contact book, the one the evaluation used.", "info");
  }
  const form = new FormData();
  form.append("clip_id", clipId);
  form.append("variant", variant);
  return process(form, { label: `Clip ${clipId} (${variant} audio)` });
}

$("#text-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const text = $("#text").value.trim();
  if (!text) { showBanner("Type a sentence first."); return; }
  runText(text);
});
function runText(text) {
  const form = new FormData();
  form.append("text", text);
  return process(form, { label: "Typed sentence" });
}

/** Send one input to /api/process and show everything that comes back. */
async function process(form, meta) {
  if (state.busy) { showBanner("Still working on the previous request…", "info"); return null; }
  state.busy = true;
  hideBanner();
  form.append("book", state.book);
  form.append("compare", state.compare ? "true" : "false");
  setLoading(meta.label);
  try {
    const result = await api("/api/process", { method: "POST", body: form });
    renderResult(result, meta);
    await loadReminders(result.reminder && result.reminder.id);
    return result;
  } catch (err) {
    showBanner(err.message);
    fill($("#base-body"), el("p", { class: "muted" }, "No result."));
    fill($("#peh-body"), el("p", { class: "muted" }, "No result: " + err.message));
    return null;
  } finally {
    state.busy = false;
  }
}

function setLoading(label) {
  $("#clarify").hidden = true;
  fill($("#input-summary"), el("p", {}, el("span", { class: "label" }, "Input"), label));
  const loading = (what) => el("div", { class: "loading" }, el("span", { class: "spinner", "aria-hidden": "true" }), what);
  fill($("#base-body"), state.compare ? loading("Asking the strong AI…") : el("p", { class: "muted" }, "Comparison is off."));
  fill($("#peh-body"), loading("Listening and deciding…"));
}

// ---------- rendering a result ----------
const nameOf = (names, id) => (id && names[id] ? names[id].name : id);
const withRole = (names, id) => {
  if (!id) return "";
  const n = names[id];
  return n ? (n.role ? `${n.name} (${n.role})` : n.name) : id;
};

/** A plain-words sentence for a decision. `stored` = Pehchaan's real reminder (or null). */
function decisionWords(d, names, stored, isPehchaan) {
  if (d.behaviour === "clarify") {
    const who = d.clarify_candidates.map((id) => nameOf(names, id));
    return "Asked: " + (who.length > 1 ? who.slice(0, -1).join(", ") + " or " + who.at(-1) : (who[0] || "someone")) + "?";
  }
  const a = d.action;
  if (a.type === "remind" && a.target_entity_id) {
    const verb = isPehchaan ? (stored ? "Created a reminder for " : "Would remind about ") : "Would create a reminder for ";
    let s = verb + withRole(names, a.target_entity_id);
    if (a.time) s += " at " + a.time;
    else if (a.raw_time_text) s += ` (“${a.raw_time_text}”, no clear clock time)`;
    if (a.place_entity_id && a.place_entity_id !== a.target_entity_id) s += ", near " + nameOf(names, a.place_entity_id);
    return s + ".";
  }
  const kept = d.entities.filter((e) => !e.resolved_entity_id).map((e) => `‘${e.heard_text}’`);
  const fixed = d.entities.filter((e) => e.resolved_entity_id).map((e) => nameOf(names, e.resolved_entity_id));
  if (fixed.length && kept.length) return `Fixed ${fixed.join(", ")}; kept ${kept.join(", ")} as heard. No reminder.`;
  if (fixed.length) return `Fixed ${fixed.join(", ")}. No reminder requested.`;
  // Say WHY it was kept, from the reason itself (v2: everyday words are not names).
  const everyday = d.entities.some((e) => !e.resolved_entity_id && /everyday/.test(e.reason));
  if (kept.length) return `Kept ${kept.join(", ")} as heard: ${everyday ? "everyday speech, not a name" : "not in your contacts"}.`;
  return "Nothing to change: no names from your contacts.";
}

/** Text with highlighted ranges. marks = [{start, end, node(textPiece) -> element}]. */
function highlighted(text, marks) {
  const p = el("p", { class: "transcript" });
  let pos = 0;
  for (const m of marks.filter((m) => m.start !== null && m.start >= 0).sort((a, b) => a.start - b.start)) {
    if (m.start < pos) continue;  // overlapping: skip
    p.append(text.slice(pos, m.start), m.node(text.slice(m.start, m.end)));
    pos = m.end;
  }
  p.append(text.slice(pos));
  return p;
}

function confChip(c) {
  const level = c >= 0.8 ? "high" : c >= 0.6 ? "mid" : "low";
  return el("span", { class: "chip " + level, title: "confidence" }, `${Math.round(c * 100)}%`);
}

function verdictLine(v) {
  if (!v) return null;
  const cls = v.ok ? "ok" : v.label.startsWith("~") ? "partial" : "bad";
  return el("p", { class: "verdict " + cls }, v.label);
}

function renderResult(r, meta) {
  const names = r.names || {};
  // What was said (only known for clips) and what speech-to-text heard.
  fill($("#input-summary"), 
    el("p", {}, el("span", { class: "label" }, "Input"), meta.label, r.book !== "default" ? ` · book ${r.book}` : ""),
    r.clip && r.clip.said ? el("p", {}, el("span", { class: "label" }, "Said"), r.clip.said) : null,
    el("p", {}, el("span", { class: "label" }, "Heard"), r.heard_transcript,
      el("span", { class: "muted small" }, `  (${r.stt_source})`)));

  // --- strong AI card ---
  if (r.baseline) {
    const b = r.baseline;
    const marks = [];
    let from = 0;
    for (const e of b.entities) {
      const written = e.resolved_entity_id ? nameOf(names, e.resolved_entity_id) : e.heard_text;
      let at = b.output_transcript.indexOf(written, from);
      let len = written.length;
      if (at < 0) { at = b.output_transcript.indexOf(e.heard_text, from); len = e.heard_text.length; }
      if (at >= 0) {
        marks.push({ start: at, end: at + len, node: (t) => el("mark", { class: "hl" + (e.resolved_entity_id ? "" : " kept"), title: e.reason }, t) });
        from = at + len;
      }
    }
    fill($("#base-body"), 
      verdictLine(r.verdict && r.verdict.baseline),
      highlighted(b.output_transcript, marks),
      el("p", { class: "decision" }, decisionWords(b, names, null, false)),
      el("p", { class: "timing" },
        el("span", {}, sttWords(r)),
        el("span", {}, "decision " + ms(r.timings.baseline_ms)),
        el("span", { class: "badge ai" }, "1 AI call"),
        el("span", {}, b.cost_usd ? usd(b.cost_usd) : "")),
      el("p", { class: "source" }, r.baseline_source || ""));
  } else {
    fill($("#base-body"), el("p", { class: "muted" }, "Comparison is off. Switch on “Compare with strong AI” in the header."));
  }

  // --- Pehchaan card ---
  const rows = [];
  const marks = [];
  r.spans.forEach((s, i) => {
    const id = "why-" + i;
    const why = el("p", { class: "why", id, hidden: true }, s.reason);
    const toggle = () => { why.hidden = !why.hidden; row.querySelector("button").setAttribute("aria-expanded", String(!why.hidden)); };
    const row = el("li", { class: "entity" },
      el("button", { type: "button", "aria-expanded": "false", "aria-controls": id, onclick: toggle },
        el("span", {}, `“${s.heard_text}”`), el("span", { class: "arrow" }, "→"),
        el("strong", {}, s.resolved_name ? (s.role ? `${s.resolved_name} (${s.role})` : s.resolved_name)
          : s.reason.startsWith("clarify") ? "asking you (see the question)" : "kept as heard"),
        confChip(s.confidence), el("span", { class: "muted small" }, "why ▾")),
      why);
    rows.push(row);
    if (s.output_start !== null) {
      marks.push({ start: s.output_start, end: s.output_end,
        node: (t) => el("button", { type: "button", class: "hl" + (s.resolved_entity_id ? "" : " kept"),
          title: `heard “${s.heard_text}” → ${s.resolved_name || "kept"}`, onclick: toggle }, t) });
    }
  });
  const d = r.decision;
  fill($("#peh-body"), 
    verdictLine(r.verdict && r.verdict.pehchaan),
    highlighted(r.output_transcript, marks),
    rows.length ? el("ul", { class: "entities", "aria-label": "Names: heard, resolved, confidence, reason" }, rows) : null,
    el("p", { class: "decision" }, decisionWords(d, names, r.reminder, true)),
    el("p", { class: "timing" },
      el("span", {}, sttWords(r)),
      el("span", {}, "decision " + ms(r.timings.pehchaan_ms)),
      el("span", { class: "badge " + (r.used_llm ? "ai" : "no-ai") }, r.used_llm ? "AI fallback used" : "No AI call"),
      el("span", {}, "cost " + usd(r.cost_usd))),
    r.pehchaan_source ? el("p", { class: "source" }, r.pehchaan_source) : null);

  renderClarify(r.pending, null);
  if (r.pending) $("#clarify").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/** How the transcript was obtained, in words (typed text has no speech-to-text step). */
function sttWords(r) {
  if (r.stt_source.startsWith("none")) return "typed: no speech-to-text";
  if (r.stt_source.startsWith("saved")) return "speech-to-text: saved transcript";
  return "speech-to-text " + ms(r.timings.stt_ms);
}

// ---------- clarify with consent ----------
function renderClarify(pending, done) {
  const box = $("#clarify");
  if (!pending) { box.hidden = true; return; }
  box.hidden = false;
  fill(box, 
    el("h3", {}, `Pehchaan asks: who is “${pending.heard_text || pending.phrase}”?`),
    el("p", { class: "muted" }, pending.reason),
    el("div", { class: "cand-list" }, pending.candidates.map((c) => el("div", { class: "cand" },
      el("span", { class: "cand-name" }, c.name),
      el("span", { class: "cand-role" }, c.reason || c.role || ""),
      el("div", { class: "cand-actions" },
        el("button", { class: "btn btn-dark btn-small", type: "button", "data-entity": c.entity_id, "data-remember": "this_time",
          onclick: () => answer(pending, c, "this_time") }, "Use this time"),
        el("button", { class: "btn btn-accent btn-small", type: "button", "data-entity": c.entity_id, "data-remember": "always",
          onclick: () => answer(pending, c, "always") }, `Always use for ‘${pending.phrase}’`))))),
    done);
}

async function answer(pending, cand, remember) {
  if (state.busy) return null;
  state.busy = true;
  hideBanner();
  $("#clarify").querySelectorAll("button").forEach((b) => { b.disabled = true; });
  try {
    const r = await api(`/api/clarify/${pending.id}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entity_id: cand.entity_id, remember }),
    });
    const rem = r.reminder;
    const msg = rem
      ? `✓ Reminder created for ${rem.target_name}${rem.target_role ? " (" + rem.target_role + ")" : ""}` +
        (rem.time ? " at " + rem.time : "") +
        (remember === "always" ? `. Learned for book ${rem.contact_book}: ‘${pending.phrase}’ = ${rem.target_name}.` : ". Nothing was learned (this time only).")
      : "Answer saved, but this sentence didn't ask for a reminder.";
    renderClarify(pending, el("p", { class: "done" }, msg));
    $("#clarify").querySelectorAll("button").forEach((b) => { b.disabled = true; });
    // Update Pehchaan's decision line to the answered decision.
    const dline = $("#peh-body .decision");
    if (dline && rem) dline.textContent = msg.replace(/^✓ /, "");
    await loadReminders(rem && rem.id);
    return r;
  } catch (err) {
    showBanner(err.message);
    $("#clarify").querySelectorAll("button").forEach((b) => { b.disabled = false; });
    return null;
  } finally {
    state.busy = false;
  }
}

// ---------- reminders ----------
let remindersById = {};
async function loadReminders(highlightId) {
  const list = await api("/api/reminders");
  remindersById = Object.fromEntries(list.map((r) => [r.id, r]));
  const ul = $("#reminders");
  if (!list.length) {
    fill(ul, el("li", { class: "muted small" }, "No reminders yet."));
    return;
  }
  fill(ul, ...list.map((r) => el("li", {},
    el("button", { class: "rem" + (r.id === highlightId ? " new" : ""), type: "button", onclick: () => openReminder(r.id) },
      el("span", { class: "rem-name" }, r.target_name || "(no person)"),
      el("span", { class: "rem-meta" }, [r.target_role, r.time ? "at " + r.time : "no clock time", "book " + r.contact_book].filter(Boolean).join(" · ")),
      el("span", { class: "res " + r.resolution }, RESOLUTION_WORDS[r.resolution] || r.resolution)))));
}

function openReminder(id) {
  const r = remindersById[id];
  if (!r) return;
  const row = (k, v) => [el("dt", {}, k), el("dd", {}, v || "–")];
  fill($("#rd-body"), 
    el("h2", { id: "rd-title" }, `Reminder #${r.id}: ${r.target_name || "(no person)"}`),
    el("dl", {},
      row("Person", r.target_name), row("Role", r.target_role),
      row("Time", r.time || (r.raw_time_text ? `“${r.raw_time_text}” (no clear clock time)` : null)),
      row("Place", r.place_name), row("Heard", r.heard_transcript), row("Resolved text", r.output_transcript),
      row("Decided by", RESOLUTION_WORDS[r.resolution] || r.resolution), row("Contact book", r.contact_book),
      row("Created", r.created_at)),
    el("h3", {}, "Heard → resolved → confidence → reason"),
    el("ul", { class: "entities" }, r.entities.map((e) => el("li", { class: "entity" },
      el("p", { class: "why" }, `“${e.heard_text}” → ${e.resolved_entity_id || "kept"} · ${Math.round(e.confidence * 100)}% · ${e.reason}`)))));
  $("#reminder-dialog").showModal();
}

$("#reset").addEventListener("click", async () => {
  if (!confirm(`Reset the demo? This deletes ALL reminders and what book ${state.book} has learned.`)) return;
  try {
    await resetDemo(state.book);
    showBanner(`Demo reset: reminders cleared, book ${state.book} forgot its learned answers.`, "info");
  } catch (err) { showBanner(err.message); }
});
async function resetDemo(book) {
  await api("/api/reminders", { method: "DELETE" });
  await api(`/api/preferences/reset?book=${encodeURIComponent(book)}`, { method: "POST" });
  $("#clarify").hidden = true;
  await loadReminders();
}

// ---------- scoreboard ----------
const SCORE_ROWS = [
  // [key, label, lower is better?]
  ["wrong_target_rate", "Wrong target (acted on the wrong person/place)", true],
  ["missed_clarification_rate", "Missed clarification (guessed instead of asking)", true],
  ["reference_resolution_accuracy", "“my doctor”, “Amma”, “the usual pharmacy” resolved right", false],
  ["exact_action_target_accuracy", "Exact action target", false],
  ["behaviour_accuracy", "Right behaviour (fix / keep / resolve / ask)", false],
  ["entity_accuracy", "Names spelled right", false],
  ["wer", "Word error rate", true],
  ["over_correction_rate", "Over-correction (changed a name that should stay)", true],
  ["unnecessary_question_rate", "Unnecessary questions", true],
  ["no_llm_rate", "Decided with no AI call", false],
];
let scoreLoaded = false;
async function loadScoreboard() {
  if (scoreLoaded) return;
  const m = await api("/api/metrics");
  const c = m.overall.c, p = m.overall.pehchaan;
  const cell = (x) => `${x.hits}/${x.total} = ${Math.round(x.rate * 100)}%`;
  $("#score-sub").textContent = m.label;
  const w = m.win_tie_loss || {};
  fill($("#score-wtl"), 
    el("div", {}, el("strong", {}, w.win ?? "–"), "Pehchaan wins"),
    el("div", {}, el("strong", {}, w.tie ?? "–"), "ties"),
    el("div", {}, el("strong", {}, w.loss ?? "–"), "losses"));
  const rows = SCORE_ROWS.filter(([k]) => c[k] && p[k]).map(([k, label, lowerBetter]) => {
    const diff = p[k].rate - c[k].rate;
    const better = lowerBetter ? diff < 0 : diff > 0;
    const word = Math.abs(diff) < 1e-9 ? ["Same", "cmp-same"] : better ? ["Better", "cmp-better"] : ["Worse", "cmp-worse"];
    return el("tr", {}, el("td", {}, label), el("td", { class: "num" }, cell(c[k])), el("td", { class: "num" }, cell(p[k])),
      el("td", { class: word[1] }, word[0]));
  });
  // Latency: the FIRST final run (the numbers on the slides), with the repeat's numbers as a note.
  const lat = m.latency_first_run || { c: { median: c.latency_ms_median, mean: c.latency_ms_mean },
                                       pehchaan: { median: p.latency_ms_median, mean: p.latency_ms_mean } };
  rows.push(el("tr", {}, el("td", {}, "Latency per decision (median / mean)",
      m.latency_note ? el("div", { class: "muted small" }, m.latency_note) : null),
    el("td", { class: "num" }, `${Math.round(lat.c.median)} / ${Math.round(lat.c.mean)} ms`),
    el("td", { class: "num" }, `${Math.round(lat.pehchaan.median)} / ${Math.round(lat.pehchaan.mean)} ms`),
    el("td", { class: "cmp-better" }, "Better")));
  rows.push(el("tr", {}, el("td", {}, "Cost per decision"),
    el("td", { class: "num" }, "$" + c.cost_usd_mean.toFixed(6)), el("td", { class: "num" }, "$" + p.cost_usd_mean.toFixed(6)),
    el("td", { class: "cmp-better" }, "Better")));
  fill($("#score-table"), 
    el("thead", {}, el("tr", {}, el("th", {}, "Metric"), el("th", {}, "Strong AI (c)"), el("th", {}, "Pehchaan"), el("th", {}, "Pehchaan is"))),
    el("tbody", {}, rows));
  renderV2(m.v2);
  scoreLoaded = true;
}

/** Second section: the v2 fix on test-2. "Better"/"Worse" compare v2 with the strong AI, in words. */
function renderV2(v2) {
  if (!v2) return;
  const { c, v1, v2: p } = v2.overall;
  const cell = (x) => (x ? `${x.hits}/${x.total} = ${Math.round(x.rate * 100)}%` : "–");
  fill($("#score-v2-sub"), v2.label);
  const w = v2.win_tie_loss || {};
  fill($("#score-v2-wtl"),
    el("div", {}, el("strong", {}, w.win ?? "–"), "v2 wins"),
    el("div", {}, el("strong", {}, w.tie ?? "–"), "ties"),
    el("div", {}, el("strong", {}, w.loss ?? "–"), "losses"));
  const rows = SCORE_ROWS.filter(([k]) => c[k] && p[k]).map(([k, label, lowerBetter]) => {
    const diff = p[k].rate - c[k].rate;
    const better = lowerBetter ? diff < 0 : diff > 0;
    const word = Math.abs(diff) < 1e-9 ? ["Same", "cmp-same"] : better ? ["Better", "cmp-better"] : ["Worse", "cmp-worse"];
    return el("tr", {}, el("td", {}, label), el("td", { class: "num" }, cell(c[k])),
      el("td", { class: "num" }, cell(v1 && v1[k])), el("td", { class: "num" }, cell(p[k])),
      el("td", { class: word[1] }, word[0]));
  });
  rows.push(el("tr", {}, el("td", {}, "Latency per decision (median / mean)"),
    el("td", { class: "num" }, `${Math.round(c.latency_ms_median)} / ${Math.round(c.latency_ms_mean)} ms`),
    el("td", { class: "num" }, v1 ? `${Math.round(v1.latency_ms_median)} / ${Math.round(v1.latency_ms_mean)} ms` : "–"),
    el("td", { class: "num" }, `${Math.round(p.latency_ms_median)} / ${Math.round(p.latency_ms_mean)} ms`),
    el("td", { class: "cmp-better" }, "Better")));
  fill($("#score-v2-table"),
    el("thead", {}, el("tr", {}, el("th", {}, "Metric"), el("th", {}, "Strong AI (c)"), el("th", {}, "Pehchaan v1"),
      el("th", {}, "Pehchaan v2"), el("th", {}, "v2 vs strong AI"))),
    el("tbody", {}, rows));
  $("#score-v2").hidden = false;
}

// ---------- live mic ----------
const MAX_RECORD_SECONDS = 15;
let recorder = null, chunks = [], timer = null, startedAt = 0;

function pickMime() {
  // Chrome/Edge/Firefox record webm/ogg (opus); Safari records mp4 (m4a). Our server accepts all of them.
  for (const type of ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"]) {
    if (window.MediaRecorder && MediaRecorder.isTypeSupported(type)) return type;
  }
  return "";
}

$("#mic").addEventListener("click", async () => {
  if (recorder && recorder.state === "recording") { recorder.stop(); return; }
  hideBanner();
  if (!window.isSecureContext || !navigator.mediaDevices) {
    showBanner("The browser only allows the microphone on https:// or on localhost. Open the https link, or run the app locally.");
    return;
  }
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    showBanner("Microphone not available: " + (err.name === "NotAllowedError" ? "permission was denied. Allow the mic in the address bar." : err.message));
    return;
  }
  const mime = pickMime();
  recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
  chunks = [];
  recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
  recorder.onstop = async () => {
    clearInterval(timer);
    stream.getTracks().forEach((t) => t.stop());  // switch the mic off (the browser's red dot goes away)
    $("#mic").classList.remove("recording");
    $("#mic").setAttribute("aria-pressed", "false");
    $("#mic-label").textContent = "Tap to record";
    const type = recorder.mimeType || mime || "audio/webm";
    const blob = new Blob(chunks, { type });
    const ext = type.includes("mp4") ? "m4a" : type.includes("ogg") ? "ogg" : "webm";
    const seconds = (Date.now() - startedAt) / 1000;
    if (seconds < 0.7 || blob.size < 1000) { showBanner("That recording was too short. Tap, speak a sentence, then tap again."); return; }
    $("#mic-note").textContent = `Sent ${seconds.toFixed(1)} s of audio (${Math.round(blob.size / 1024)} KB, ${ext}).`;
    const form = new FormData();
    form.append("file", blob, "mic." + ext);
    await process(form, { label: `Your voice (${seconds.toFixed(1)} s)` });
  };
  recorder.start();
  startedAt = Date.now();
  $("#mic").classList.add("recording");
  $("#mic").setAttribute("aria-pressed", "true");
  $("#mic-label").textContent = "Recording… tap to stop";
  timer = setInterval(() => {
    const s = Math.floor((Date.now() - startedAt) / 1000);
    $("#mic-time").textContent = `0:${String(Math.min(s, MAX_RECORD_SECONDS)).padStart(2, "0")}`;
    if (s >= MAX_RECORD_SECONDS && recorder.state === "recording") recorder.stop();  // hard 15 s limit
  }, 200);
});

// ---------- demo mode: the doctor story, one Next click per step ----------
const SENTENCE = "Remind me to call my doctor at 6 PM.";
let lastResult = null;
const STEPS = [
  { text: "Same sentence, two users. Book A has ONE doctor.", run: async () => {
      await resetDemo("B");
      setBook("A"); $("#text").value = SENTENCE;
      lastResult = await runText(SENTENCE);
    }, after: "Book A: only one doctor, so Pehchaan creates the reminder for Dr. Venkataramana. No question." },
  { text: "Now user B: two doctors and no default. Same sentence.", run: async () => {
      setBook("B");
      lastResult = await runText(SENTENCE);
    }, after: "Book B: two doctors fit ‘my doctor’ and nothing separates them, so Pehchaan ASKS instead of guessing. The strong AI guesses." },
  { text: "The user taps “Always use Dr. Subramanian for ‘my doctor’”.", run: async () => {
      const p = lastResult && lastResult.pending;
      if (!p) throw new Error("No question is open. Run the previous step again.");
      const c = p.candidates.find((x) => x.name === "Dr. Subramanian") || p.candidates[0];
      await answer(p, c, "always");
    }, after: "A reminder for Dr. Subramanian, and book B learned it, only because the user chose ‘always’." },
  { text: "Book B says the same sentence again.", run: async () => {
      lastResult = await runText(SENTENCE);
    }, after: "No question this time: resolved from the learned preference (see ‘learned preference’ on the reminder)." },
  { text: "“Call my doctor about my fever.”", run: async () => {
      const t = "Call my doctor about my fever.";
      $("#text").value = t;
      lastResult = await runText(t);
    }, after: "‘fever’ is a clue for the general physician: a clue in the sentence beats the saved choice. Demo complete." },
];
let stepIndex = -1;

function showGuide(stepLabel, text, nextLabel) {
  $("#guide").hidden = false;
  $("#guide-step").textContent = stepLabel;
  $("#guide-text").textContent = text;
  $("#guide-next").textContent = nextLabel;
}
$("#demo-mode").addEventListener("click", () => {
  stepIndex = -1;
  document.querySelector('.tab[data-view="demo"]').click();
  showGuide("Demo mode", "The doctor story in " + STEPS.length + " steps. Click Next to run each step.", "Start ▶");
});
$("#guide-exit").addEventListener("click", () => { $("#guide").hidden = true; });
$("#guide-next").addEventListener("click", async () => {
  if (stepIndex >= STEPS.length - 1) { $("#guide").hidden = true; return; }
  stepIndex += 1;
  const step = STEPS[stepIndex];
  const label = `Step ${stepIndex + 1} of ${STEPS.length}`;
  showGuide(label, step.text, "Working…");
  $("#guide-next").disabled = true;
  try {
    await step.run();
    showGuide(label, step.after, stepIndex === STEPS.length - 1 ? "Finish" : "Next ▶");
  } catch (err) {
    showBanner(err.message);
    stepIndex -= 1;  // let the presenter retry this step
    showGuide(label, "That step failed: " + err.message, "Retry ▶");
  } finally {
    $("#guide-next").disabled = false;
  }
});

// ---------- start ----------
(async function init() {
  try { state.demoKey = sessionStorage.getItem("pehchaan-demo-key"); } catch (_) { /* storage blocked */ }
  $("#mic-label").textContent = "Tap to record";
  if (!window.isSecureContext) {
    $("#mic-note").textContent = "The mic needs https:// or localhost. Clips and typing work here.";
  }
  try {
    state.config = await api("/api/config");
    if (state.config.demo_key_required && !state.demoKey) askForKey();
    await Promise.all([loadBooks(), loadClips(), loadReminders()]);
  } catch (err) {
    showBanner(err.message);
  }
})();
