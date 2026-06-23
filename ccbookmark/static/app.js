"use strict";

const $ = (sel) => document.querySelector(sel);
const el = (tag, props = {}, ...kids) => {
  const node = Object.assign(document.createElement(tag), props);
  for (const k of kids) node.append(k);
  return node;
};

async function api(path, opts) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add("hidden"), 3200);
}

// ---- Tabs -----------------------------------------------------------------
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const which = tab.dataset.tab;
    $("#saved-panel").classList.toggle("hidden", which !== "saved");
    $("#live-panel").classList.toggle("hidden", which !== "live");
    if (which === "live") loadLive();
    else loadSaved();
  });
});

// ---- Saved list -----------------------------------------------------------
async function loadSaved() {
  const q = $("#search").value.trim();
  const tag = $("#tag").value.trim();
  const params = new URLSearchParams();
  if (q) params.set("query", q);
  if (tag) params.set("tag", tag);
  const rows = await api("/api/sessions?" + params.toString());
  const tbody = $("#saved-rows");
  tbody.replaceChildren();
  $("#saved-empty").classList.toggle("hidden", rows.length > 0);
  for (const r of rows) {
    const tr = el(
      "tr",
      {},
      el("td", {}, r.title || r.session_id),
      el("td", { className: "cwd", title: r.cwd }, r.cwd || "—"),
      el("td", {}, `${r.user_count}/${r.assistant_count}`),
      el("td", {}, (r.saved_at || "").slice(0, 10)),
      el("td", {}, viewButton(() => openDetail(r.session_id))),
    );
    tr.addEventListener("click", (e) => {
      if (e.target.tagName !== "BUTTON") openDetail(r.session_id);
    });
    tbody.append(tr);
  }
}

// ---- Live list ------------------------------------------------------------
async function loadLive() {
  const cwd = $("#live-cwd").value.trim();
  const params = new URLSearchParams();
  if (cwd) params.set("cwd", cwd);
  const rows = await api("/api/live?" + params.toString());
  const tbody = $("#live-rows");
  tbody.replaceChildren();
  $("#live-empty").classList.toggle("hidden", rows.length > 0);
  for (const r of rows) {
    const action = r.saved
      ? el("span", { className: "badge saved" }, "saved")
      : saveButton(r.session_id);
    const tr = el(
      "tr",
      {},
      el("td", {}, r.title || r.session_id),
      el("td", { className: "cwd", title: r.cwd }, r.cwd || "—"),
      el("td", {}, `${r.user_count}/${r.assistant_count}`),
      el("td", {}, (r.last_ts || "").slice(0, 19).replace("T", " ")),
      el("td", {}, action),
    );
    tbody.append(tr);
  }
}

function viewButton(onClick) {
  const b = el("button", { className: "row-btn" }, "View");
  b.addEventListener("click", (e) => { e.stopPropagation(); onClick(); });
  return b;
}

function saveButton(sessionId) {
  const b = el("button", { className: "row-btn" }, "Save");
  b.addEventListener("click", async (e) => {
    e.stopPropagation();
    try {
      await api("/api/sessions/save", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId }),
      });
      toast("Saved");
      loadLive();
    } catch (err) {
      toast("Error: " + err.message);
    }
  });
  return b;
}

// ---- Detail drawer --------------------------------------------------------
let current = null;

async function openDetail(sessionId) {
  const r = await api("/api/sessions/" + encodeURIComponent(sessionId));
  current = r;
  $("#d-title").textContent = r.title || r.session_id;
  $("#d-id").textContent = r.session_id;
  const meta = $("#d-meta");
  meta.replaceChildren();
  const pairs = [
    ["cwd", r.cwd],
    ["branch", r.git_branch],
    ["version", r.version],
    ["messages", `${r.user_count} user / ${r.assistant_count} assistant`],
    ["tokens", `${r.total_input_tokens} in / ${r.total_output_tokens} out`],
    ["tags", (r.tags || []).join(", ") || "—"],
    ["saved", r.saved_at],
  ];
  for (const [k, v] of pairs) {
    meta.append(el("dt", {}, k), el("dd", {}, String(v ?? "—")));
  }
  $("#d-summary").textContent = r.summary || "(none)";
  const files = r.files || [];
  $("#d-files-h").classList.toggle("hidden", files.length === 0);
  const ul = $("#d-files");
  ul.replaceChildren(...files.map((f) => el("li", {}, f)));
  $("#d-command").classList.add("hidden");
  $("#drawer").classList.remove("hidden");
}

$("#drawer-close").addEventListener("click", () => $("#drawer").classList.add("hidden"));

function showCommand(cmd) {
  const c = $("#d-command");
  c.textContent = cmd;
  c.classList.remove("hidden");
}

$("#d-command").addEventListener("click", () => {
  navigator.clipboard?.writeText($("#d-command").textContent).then(() => toast("Command copied"));
});

$("#d-restore").addEventListener("click", async () => {
  try {
    const res = await api(`/api/sessions/${encodeURIComponent(current.session_id)}/restore`, { method: "POST" });
    showCommand(res.command);
    toast(res.restored ? "Restored to project dir" : "Already present — ready to resume");
  } catch (err) { toast("Error: " + err.message); }
});

$("#d-export").addEventListener("click", async () => {
  const target = prompt("Export into which project dir (absolute cwd)?", current.cwd || "");
  if (!target) return;
  const newId = confirm("Assign a fresh session id? (recommended to avoid collisions)");
  try {
    const res = await api(`/api/sessions/${encodeURIComponent(current.session_id)}/export`, {
      method: "POST",
      body: JSON.stringify({ target_cwd: target, new_id: newId }),
    });
    showCommand(res.command);
    toast("Exported");
  } catch (err) { toast("Error: " + err.message); }
});

$("#d-delete").addEventListener("click", async () => {
  if (!confirm("Delete this saved conversation?")) return;
  const purge = confirm("Also delete the archived JSONL copy? (OK = purge)");
  try {
    await api(`/api/sessions/${encodeURIComponent(current.session_id)}?purge=${purge}`, { method: "DELETE" });
    $("#drawer").classList.add("hidden");
    toast("Deleted");
    loadSaved();
  } catch (err) { toast("Error: " + err.message); }
});

// ---- Wire up --------------------------------------------------------------
$("#refresh-saved").addEventListener("click", loadSaved);
$("#refresh-live").addEventListener("click", loadLive);
$("#search").addEventListener("input", debounce(loadSaved, 250));
$("#tag").addEventListener("input", debounce(loadSaved, 250));

function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

loadSaved();
