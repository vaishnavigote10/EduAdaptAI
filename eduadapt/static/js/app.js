(() => {
const $ = (s, r = document) => r.querySelector(s);
const stage = $("#stage");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const csrf = () => (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";
const api = async (url, opts = {}) => {
  const r = await fetch(url, { credentials: "same-origin", ...opts, headers: { "X-CSRFToken": csrf(), ...(opts.body && !(opts.body instanceof FormData) ? { "Content-Type": "application/json" } : {}), ...opts.headers } });
  if (r.status === 401) { location.href = "/login"; throw new Error("Please sign in."); }
  const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.error || `Server error (${r.status}). Check the terminal running the server for details.`); return j;
};
const post = (u, b) => api(u, { method: "POST", body: b instanceof FormData ? b : JSON.stringify(b || {}) });
const toast = m => { const t = $("#toast"); t.textContent = m; t.classList.add("show"); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 2800); };
const pct = p => Math.round(p * 100);
const colour = p => p >= .6 ? "#7fe0b0" : p >= .4 ? "#f2b84b" : "#ff7a66";
let view = "dashboard", D = null;

document.querySelectorAll("#nav button").forEach(b => b.onclick = () => go(b.dataset.view));
$("#logoutBtn").onclick = async () => { await post("/api/auth/logout").catch(() => {}); location.href = "/login"; };
$("#resetBtn").onclick = async () => { if (confirm("Reset your quiz history and mastery?")) { await post("/api/reset"); toast("Progress reset"); go(view); } };

async function loadCourses() {
  const r = await api("/api/courses"), sel = $("#courseSel");
  sel.innerHTML = r.courses.length ? (r.current ? "" : `<option value="" selected disabled>Choose a course…</option>`) + r.courses.map(c => `<option value="${c.id}" ${c.id === r.current ? "selected" : ""}>${esc(c.name)}</option>`).join("") : `<option>No course yet</option>`;
  sel.disabled = !r.courses.length; $("#delCourse").disabled = !r.current;
  return r;
}
$("#courseSel").onchange = async e => { if (!e.target.value) return; await post("/api/courses/select", { id: +e.target.value }); go(view); };
$("#newCourse").onclick = () => { $("#cName").value = ""; $("#dlg").showModal(); $("#cName").focus(); };
$("#cCancel").onclick = () => $("#dlg").close();
$("#courseForm").onsubmit = async e => {
  e.preventDefault();
  try { await post("/api/courses/create", { name: $("#cName").value }); $("#dlg").close(); await loadCourses(); toast("Course created. Add your material."); go("library"); }
  catch (err) { toast(err.message); }
};
$("#delCourse").onclick = async () => { const n = $("#courseSel").selectedOptions[0]?.textContent; if (n && confirm(`Delete "${n}" and all its material and progress?`)) { await post("/api/courses/delete", { id: +$("#courseSel").value }); await loadCourses(); go("dashboard"); } };

async function go(v, arg) {
  view = v;
  document.querySelectorAll("#nav button").forEach(b => b.classList.toggle("on", b.dataset.view === v));
  stage.innerHTML = ""; window.scrollTo(0, 0);
  try {
    if (v === "team") return team();
    const c = await loadCourses();
    if (!c.current) return chooser(c);
    await ({ dashboard, tutor, quiz, library, studio })[v](arg);
  } catch (e) { stage.innerHTML = `<div class="panel empty"><h2>That didn't load</h2><p class="sub">${esc(e.message)}</p></div>`; }
}

function emptyState() { loadCourses().then(chooser); }

function chooser(c) {
  const list = c.courses || [];
  if (!list.length) {
    stage.innerHTML = `<div class="panel" style="max-width:640px;margin:8vh auto 0;padding:34px"><h1 style="font-size:clamp(28px,3.4vw,40px)">What do you want to learn?</h1>
    <p class="sub">Name your course or subject. Next you'll add your own files or notes, and the tutor, quizzes and notes are all built from them.</p>
    <form id="firstCourse" style="display:flex;gap:10px;margin-top:22px;flex-wrap:wrap"><input id="fcName" required maxlength="120" aria-label="Course or subject" placeholder="e.g. Data Structures, Organic Chemistry, UPSC History" style="flex:1 1 260px;font:inherit;font-size:16px;color:var(--chalk);background:rgba(0,0,0,.3);border:1px solid var(--line);border-radius:12px;padding:13px 14px;outline:none"><button class="btn">Start learning</button></form></div>`;
    $("#fcName").focus();
    $("#firstCourse").onsubmit = async e => { e.preventDefault(); try { await post("/api/courses/create", { name: $("#fcName").value }); toast("Course created. Now add your material."); go("library"); } catch (err) { toast(err.message); } };
    return;
  }
  stage.innerHTML = `<h1>Choose your course</h1><p class="sub">The tutor's answers, quizzes, notes and your progress all belong to the course you pick. Create one for each subject you study.</p>
  <div class="studio">${list.map(x => `<button class="panel pick" data-id="${x.id}" style="text-align:left"><h2>${esc(x.name)}</h2><p class="sub" style="margin:8px 0 0">${x.docs} file${x.docs === 1 ? "" : "s"} · ${x.topics} topic${x.topics === 1 ? "" : "s"}</p></button>`).join("")}
  <button class="panel pick" id="mk" style="text-align:left;border-style:dashed"><h2>+ New course</h2><p class="sub" style="margin:8px 0 0">Another subject to learn.</p></button></div>`;
  document.querySelectorAll(".pick[data-id]").forEach(b => b.onclick = async () => { await post("/api/courses/select", { id: +b.dataset.id }); go("dashboard"); });
  $("#mk").onclick = () => $("#newCourse").click();
}

async function dashboard() {
  D = await api("/api/dashboard"); if (D.empty) return emptyState();
  if (!D.topics.length) { stage.innerHTML = `<h1>${esc(D.course)}</h1><div class="panel empty" style="margin-top:26px"><h2>Add material to get started</h2><p class="sub" style="margin:0 auto 22px">EduAdapt builds topics, a tutor and quizzes from whatever you add.</p><button class="btn" id="al">Add material</button></div>`; $("#al").onclick = () => go("library"); return; }
  const acc = D.accuracy == null ? "–" : pct(D.accuracy) + "%";
  stage.innerHTML = `
  <h1>${esc(D.course)}</h1><p class="sub">${D.learner && D.learner !== "Learner" ? esc(D.learner) + ", your" : "Your"} learner profile updates after every answer. Weak spots surface first, strong topics get harder questions.</p>
  <div class="grid g-hero">
    <section class="panel hero"><div class="ring" id="ring"><div><span><strong>${pct(D.overall)}%</strong><small>overall mastery</small></span></div></div>
      <div class="stats"><div class="stat"><b>${D.streak}</b><span>day streak</span></div><div class="stat"><b>${acc}</b><span>accuracy</span></div>
      <div class="stat"><b>${D.answered}</b><span>questions answered</span></div><div class="stat"><b>${D.chunks}</b><span>sources indexed</span></div></div></section>
    <section class="panel"><h2>Up next</h2>${D.recommendations.map((r, i) => `<button class="rec" data-i="${i}"><div class="pill building">${i + 1}</div><div><b>${esc(r.title)}</b><span>${esc(r.why)}</span></div></button>`).join("")}</section>
  </div>
  <div class="grid g-2" style="margin-top:18px">
    <section class="panel"><h2>Knowledge map</h2><p class="sub" style="margin-top:4px">Topic size shows how much material you have. Colour shows how well you know it. Lines show prerequisites.</p><svg id="map" viewBox="0 0 760 330" role="img" aria-label="Knowledge map"></svg>
      <div class="legend"><span><i style="background:#ff7a66"></i>Weak</span><span><i style="background:#f2b84b"></i>Building</span><span><i style="background:#7fe0b0"></i>Strong</span></div></section>
    <section class="panel"><h2>Topic mastery</h2>${D.topics.map(t => `<div class="trow"><div class="top"><span>${esc(t.name)}</span><em>${pct(t.p)}% · <span class="pill ${t.level}">${t.level}</span></em></div><div class="bar"><i style="--w:0%" data-w="${pct(t.p)}%"></i></div></div>`).join("")}</section>
  </div>
  <div class="grid g-3" style="margin-top:18px">
    <section class="panel"><h2>Misconceptions</h2>${D.misconceptions.length ? D.misconceptions.map(m => `<div class="miscon"><b>${esc(m.topic)}</b><br>You picked “${esc(m.chose)}” where the answer was “${esc(m.expected)}”${m.times > 1 ? ` (${m.times}×)` : ""}.</div>`).join("") : `<p class="sub">None detected yet. Answer a few questions and repeated wrong picks will appear here.</p>`}</section>
    <section class="panel"><h2>Recent activity</h2>${D.recent.length ? D.recent.map(r => `<div class="trow top" style="display:flex;justify-content:space-between;margin-top:11px;font-size:14px"><span>${esc(r.topic)}</span><span class="pill ${r.correct ? "strong" : "weak"}">${r.correct ? "Correct" : "Missed"}</span></div>`).join("") : `<p class="sub">Your answers will show up here.</p>`}</section>
    <section class="panel"><h2>The learning loop</h2><p class="sub" style="margin-top:8px">Learn → Ask → Assess → Analyze → Adapt. Each answer updates a Bayesian mastery estimate that picks your next question.</p><div style="margin-top:18px;display:grid;gap:8px"><button class="btn" id="goQuiz">Start practice</button><button class="btn alt" id="goDiag">Run diagnostic</button></div></section>
  </div>`;
  requestAnimationFrame(() => { $("#ring").style.setProperty("--p", pct(D.overall)); document.querySelectorAll(".bar>i[data-w]").forEach(i => { i.style.setProperty("--w", i.dataset.w); }); });
  document.querySelectorAll(".rec").forEach(b => b.onclick = () => { const r = D.recommendations[b.dataset.i]; r.action === "notes" ? window.open(`/api/topics/${r.topic}/notes`, "_blank") : go(r.action); });
  $("#goQuiz").onclick = () => go("quiz"); $("#goDiag").onclick = () => go("quiz", "diagnostic");
  drawMap();
}

function drawMap() {
  const svg = $("#map"), T = D.topics, n = T.length, pos = {};
  T.forEach((t, i) => { pos[t.id] = { x: 90 + (580 * i) / Math.max(1, n - 1), y: 165 + (i % 2 ? 62 : -62) * (n > 1 ? 1 : 0) }; });
  const maxC = Math.max(...T.map(t => t.chunks), 1);
  let s = `<defs><filter id="glow"><feGaussianBlur stdDeviation="6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>`;
  T.forEach(t => t.prereqs.forEach(p => { if (pos[p]) s += `<line x1="${pos[p].x}" y1="${pos[p].y}" x2="${pos[t.id].x}" y2="${pos[t.id].y}" stroke="rgba(237,239,230,.22)" stroke-width="2" stroke-dasharray="5 6"/>`; }));
  T.forEach(t => { const { x, y } = pos[t.id], r = 28 + 18 * (t.chunks / maxC), c = colour(t.p);
    s += `<g class="node" data-id="${t.id}" style="transform-origin:${x}px ${y}px"><circle cx="${x}" cy="${y}" r="${r + 8}" fill="${c}" opacity=".12"/><circle cx="${x}" cy="${y}" r="${r}" fill="#0b1713" stroke="${c}" stroke-width="3" filter="url(#glow)"/>
    <circle cx="${x}" cy="${y}" r="${r - 6}" fill="${c}" opacity="${.15 + t.p * .6}"/><text x="${x}" y="${y + 5}" style="font-size:14px;font-weight:800">${pct(t.p)}%</text><text x="${x}" y="${y + r + 22}">${esc(t.name.length > 22 ? t.name.slice(0, 21) + "…" : t.name)}</text></g>`; });
  svg.innerHTML = s;
  svg.querySelectorAll(".node").forEach(g => g.onclick = () => go("studio"));
}

async function tutor() {
  const T = (await api("/api/dashboard")).topics || [];
  const sugg = T.slice(0, 3).map(t => `Explain ${t.name}`).concat(["Summarise the key points"]);
  stage.innerHTML = `<h1>AI Tutor</h1><p class="sub">Answers come from your own material, with the page, slide or video timestamp they were found at. If the material doesn't cover it, the tutor says so.</p>
  <div class="chat" id="chat"><div class="msg ai">Ask me anything about <b>${esc($("#courseSel").selectedOptions[0]?.textContent || "your course")}</b>. I only answer from the material you added to it.</div></div>
  <div class="chips" id="chips">${sugg.map(q => `<button class="chip">${esc(q)}</button>`).join("")}</div>
  <form class="ask" id="askForm" style="margin-top:18px"><input id="q" placeholder="Ask a question…" autocomplete="off" aria-label="Your question"><button class="btn">Ask</button></form>`;
  const chat = $("#chat");
  async function send(q) {
    if (!q.trim()) return; $("#q").value = "";
    chat.insertAdjacentHTML("beforeend", `<div class="msg me">${esc(q)}</div>`);
    chat.insertAdjacentHTML("beforeend", `<div class="msg ai" id="wait"><span class="dots"><span></span><span></span><span></span></span></div>`);
    try {
      const r = await post("/api/ask", { question: q }); $("#wait").remove();
      chat.insertAdjacentHTML("beforeend", `<div class="msg ai ${r.grounded ? "" : "warn"}"><span class="badge ${r.grounded ? "" : "no"}">${r.grounded ? "Grounded in your course · " + pct(r.confidence) + "% match" : "Not in your course material"}</span><div>${esc(r.answer)}</div>
        ${r.citations.length ? `<div class="cites">${r.citations.map(c => `<div class="cite"><b>${esc(c.doc)} · ${esc(c.location)}</b>${esc(c.snippet)}…</div>`).join("")}</div>` : ""}</div>`);
    } catch (e) { $("#wait").remove(); chat.insertAdjacentHTML("beforeend", `<div class="msg ai warn">${esc(e.message)}</div>`); }
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  }
  $("#askForm").onsubmit = e => { e.preventDefault(); send($("#q").value); };
  document.querySelectorAll(".chip").forEach(c => c.onclick = () => send(c.textContent));
}

async function quiz(mode = "adaptive") {
  const letters = "ABCD";
  async function next() {
    const r = await api("/api/quiz/next?mode=" + mode);
    if (r.done) { stage.innerHTML = `<div class="panel empty"><h2>Diagnostic complete</h2><p class="sub" style="margin:0 auto 22px">${esc(r.message)}</p><button class="btn" id="d">See my dashboard</button></div>`; $("#d").onclick = () => go("dashboard"); return; }
    const q = r.question;
    stage.innerHTML = `<h1>${mode === "diagnostic" ? "Diagnostic" : "Practice"}</h1><p class="sub">${mode === "diagnostic" ? "One question per topic to find your starting point." : "Questions are chosen from your weakest topic at the right difficulty."}</p>
    <div class="qwrap panel"><div class="qtop"><span>${esc(q.topic)}</span><span class="pill">${["", "Easy", "Medium", "Hard"][q.difficulty]} · mastery ${pct(r.mastery)}%</span></div>
    <div class="qprompt">${esc(q.prompt)}</div><div class="opts">${q.options.map((o, i) => `<button class="opt" data-o="${esc(o)}"><b>${letters[i]}</b>${esc(o)}</button>`).join("")}</div><div id="fb"></div></div>`;
    document.querySelectorAll(".opt").forEach(b => b.onclick = async () => {
      document.querySelectorAll(".opt").forEach(x => x.disabled = true);
      const a = await post("/api/quiz/answer", { question: q.id, answer: b.dataset.o });
      document.querySelectorAll(".opt").forEach(x => { if (x.dataset.o === a.answer) x.classList.add("right"); });
      if (!a.correct) b.classList.add("wrong");
      const up = a.after >= a.before;
      $("#fb").innerHTML = `<div class="fb"><b style="color:${a.correct ? "#7fe0b0" : "#ff7a66"}">${a.correct ? "Correct." : "Not quite. The answer is “" + esc(a.answer) + "”."}</b><p style="margin-top:8px;color:#9fb2a8">${esc(a.explanation)}</p>
      <div class="delta"><span>${esc(a.topic)}</span><div class="bar"><i style="--w:${pct(a.before)}%"></i></div><span style="color:${up ? "#7fe0b0" : "#ff7a66"}">${pct(a.before)}% → ${pct(a.after)}%</span></div>
      <div style="margin-top:18px;display:flex;gap:10px"><button class="btn" id="nx">Next question</button><button class="btn alt" id="dn">Finish</button></div></div>`;
      requestAnimationFrame(() => { const i = $(".delta .bar>i"); i.style.setProperty("--w", pct(a.after) + "%"); });
      $("#nx").onclick = next; $("#dn").onclick = () => go("dashboard");
    });
  }
  try { await next(); } catch (e) { stage.innerHTML = `<div class="panel empty"><h2>No questions yet</h2><p class="sub" style="margin:0 auto 20px">${esc(e.message)}</p><button class="btn" id="l">Add material</button></div>`; $("#l").onclick = () => go("library"); }
}

async function library() {
  const cname = $("#courseSel").selectedOptions[0]?.textContent || "";
  stage.innerHTML = `<h1>Course library</h1><p class="sub" style="margin-top:6px">Adding to: <b>${esc(cname)}</b></p>
  <p class="sub">PDF, Word (.docx), PowerPoint (.pptx), transcripts (.vtt, .srt, or .txt with [mm:ss] timestamps) and plain text.</p>
  <div class="drop" id="drop"><h2>Drop files here</h2><p>PDF · DOCX · PPTX · VTT/SRT · TXT/MD</p><input type="file" id="file" multiple hidden accept=".pdf,.docx,.pptx,.vtt,.srt,.txt,.md,.mp4,.mp3,.wav,.png,.jpg"><button class="btn" id="pick" type="button">Choose files</button></div>
  <div id="report"></div>
  <form class="panel paste" id="pasteForm"><h2>Or paste your notes</h2><input id="pTitle" placeholder="Title, e.g. Chapter 4 notes" maxlength="200"><textarea id="pText" placeholder="Paste text from a textbook, your notes or a transcript…"></textarea><div><button class="btn alt">Add notes</button></div></form>
  <div class="docs" id="docs"></div>`;
  const drop = $("#drop"), input = $("#file"), rep = $("#report");
  const tag = { pdf: "PDF", pptx: "PPT", docx: "DOC", video: "VID", text: "TXT", image: "IMG" };
  async function refreshDocs() {
    const L = await api("/api/library");
    $("#docs").innerHTML = L.docs.length ? L.docs.map(d => `<div class="doc"><div class="ic">${tag[d.kind] || "DOC"}</div><div><b>${esc(d.title)}</b><small>${d.chunks} indexed chunks · added ${d.added}</small></div></div>`).join("") : `<p class="sub">No files in this course yet.</p>`;
  }
  function report(ok, errs) {
    rep.innerHTML = `<div class="panel" style="margin-top:18px">${ok.map(a => `<div class="miscon" style="border-color:#7fe0b0;background:rgba(127,224,176,.08)"><b>${esc(a.title)}</b> added: ${a.chunks} chunks indexed, ${a.topics} topic${a.topics === 1 ? "" : "s"} in this course.</div>`).join("")}
    ${errs.map(e => `<div class="miscon"><b>${esc(e.file || "Upload")}</b> could not be added: ${esc(e.error)}</div>`).join("")}
    ${ok.length ? `<div style="margin-top:14px;display:flex;gap:10px"><button class="btn" id="toDash" type="button">Open dashboard</button><button class="btn alt" id="toTutor" type="button">Ask the tutor</button></div>` : ""}</div>`;
    const d = $("#toDash"); if (d) { d.onclick = () => go("dashboard"); $("#toTutor").onclick = () => go("tutor"); }
  }
  async function upload(files) {
    if (!files.length) return; const fd = new FormData(); [...files].forEach(f => fd.append("files", f));
    const btn = $("#pick"); btn.textContent = "Reading and indexing…"; btn.disabled = true;
    rep.innerHTML = `<p class="sub" style="margin-top:14px">Processing ${files.length} file${files.length > 1 ? "s" : ""}. Large PDFs can take a moment.</p>`;
    try { const r = await post("/api/upload", fd); report(r.added, r.errors); } catch (e) { report([], [{ error: e.message }]); }
    btn.textContent = "Choose files"; btn.disabled = false; input.value = ""; refreshDocs();
  }
  $("#pick").onclick = () => input.click(); input.onchange = () => upload(input.files);
  ["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", e => upload(e.dataTransfer.files));
  $("#pasteForm").onsubmit = async e => {
    e.preventDefault();
    try { const r = await post("/api/paste", { title: $("#pTitle").value, text: $("#pText").value }); report([{ title: r.title, chunks: r.chunks, topics: r.topics }], []); $("#pText").value = ""; $("#pTitle").value = ""; refreshDocs(); }
    catch (err) { report([], [{ file: "Pasted notes", error: err.message }]); }
  };
  refreshDocs();
}

function team() {
  const T = JSON.parse($("#team-data").textContent);
  stage.innerHTML = `<h1>The team behind EduAdapt AI</h1><p class="sub">A source-grounded tutor and adaptive learning platform, built for the Multimodal AI Hackathon 2026 (Track D: Personalized Tutoring &amp; Adaptive Learning).</p>
  <div class="studio">${T.map(m => `<section class="panel member"><div class="av">${esc(m.initial)}</div><div><b>${esc(m.name)}</b><span>${esc(m.role)}</span></div></section>`).join("")}</div>`;
}

async function studio() {
  D = await api("/api/dashboard"); if (D.empty) return emptyState();
  stage.innerHTML = `<h1>Study Studio</h1><p class="sub">Generate a slide deck or handwritten-style notes for any topic, built only from your uploaded sources.</p>
  <div class="studio">${D.topics.map(t => `<section class="panel"><span class="pill ${t.level}">${t.level} · ${pct(t.p)}%</span><h2>${esc(t.name)}</h2><p class="sub" style="margin:0">${t.chunks} source chunks · ${t.questions} practice questions</p>
  <div class="row"><a class="btn" href="/api/topics/${t.id}/notes" target="_blank" rel="noopener">Handwritten notes</a><a class="btn alt" href="/api/topics/${t.id}/ppt">Download PPT</a></div></section>`).join("")}</div>`;
}
go("dashboard");
})();
