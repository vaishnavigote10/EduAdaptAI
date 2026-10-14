(() => {
  const $ = s => document.querySelector(s);
  const csrf = () => (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";
  let mode = "in";
  const post = async (url, body) => {
    const r = await fetch(url, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() }, body: JSON.stringify(body || {}) });
    const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.error || `Server error (${r.status}).`); return j;
  };
  document.querySelectorAll(".tabs button").forEach(b => b.onclick = () => {
    mode = b.dataset.tab; document.querySelectorAll(".tabs button").forEach(x => x.classList.toggle("on", x === b));
    $("#nameRow").hidden = mode === "in"; $("#go").textContent = mode === "in" ? "Sign in" : "Create account";
    $("#aPass").autocomplete = mode === "in" ? "current-password" : "new-password"; $("#err").textContent = "";
  });
  async function run(fn, btn, label) {
    btn.disabled = true; btn.textContent = "One moment…"; $("#err").textContent = "";
    try { await fn(); location.href = "/"; } catch (e) { $("#err").textContent = e.message; btn.disabled = false; btn.textContent = label; }
  }
  $("#authForm").onsubmit = e => { e.preventDefault(); const lbl = mode === "in" ? "Sign in" : "Create account";
    run(() => post(mode === "in" ? "/api/auth/login" : "/api/auth/register", { name: $("#aName").value, email: $("#aEmail").value, password: $("#aPass").value }), $("#go"), lbl); };
  $("#demoBtn").onclick = () => run(() => post("/api/auth/demo"), $("#demoBtn"), "Continue as Demo Student");
})();
