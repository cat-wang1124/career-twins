// =============================================================
// Career Twin Finder — frontend logic
// Plain ES modules, no build step. Talks to /api/twins.
// =============================================================

const $ = (sel) => document.querySelector(sel);

// ---------- state ----------
let mode = "url";   // "url" | "text"
let numTwins = 20;

// ---------- tabs ----------
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    mode = btn.dataset.mode;
    document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("tab--active", b === btn));
    document.querySelectorAll(".composer__field").forEach((f) => {
      f.classList.toggle("hidden", f.dataset.field !== mode);
    });
    hideError();
  });
});

// ---------- num toggle ----------
document.querySelectorAll(".num-toggle button").forEach((btn) => {
  btn.addEventListener("click", () => {
    numTwins = parseInt(btn.dataset.n, 10);
    document
      .querySelectorAll(".num-toggle button")
      .forEach((b) => b.classList.toggle("num-toggle__active", b === btn));
  });
});

// ---------- submit ----------
$("#submit").addEventListener("click", run);
$("#url-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") run();
});

async function run() {
  hideError();
  const query = (mode === "url" ? $("#url-input").value : $("#text-input").value).trim();
  if (!query) {
    showError("Enter a LinkedIn URL or paste résumé text.");
    return;
  }
  if (mode === "url" && !/linkedin\.com\/in\//i.test(query)) {
    showError("URL doesn't look like a LinkedIn profile. Try one starting with linkedin.com/in/…");
    return;
  }
  if (mode === "text" && query.length < 200) {
    showError("Résumé text needs to be at least 200 characters — give us something to work with.");
    return;
  }

  setLoading(true);

  try {
    const res = await fetch("/api/twins", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, num_twins: numTwins, use_cache: true }),
    });

    if (!res.ok) {
      const detail = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(detail.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    renderResults(data);
  } catch (err) {
    showError(err.message || "Something went wrong.");
    hideResults();
  } finally {
    setLoading(false);
  }
}

// ---------- rendering ----------
function renderResults(data) {
  const list = $("#twin-list");
  list.innerHTML = "";

  const tpl = $("#twin-template");
  data.twins.forEach((twin, i) => {
    const li = tpl.content.firstElementChild.cloneNode(true);
    li.style.animationDelay = `${i * 0.04}s`;

    li.querySelector(".twin__index").textContent = String(i + 1).padStart(2, "0");
    li.querySelector(".twin__name").textContent = twin.name || "Unknown";

    const role = li.querySelector(".twin__role");
    if (twin.current_role_guess) {
      role.textContent = twin.current_role_guess;
    } else {
      role.classList.add("hidden");
    }

    const why = li.querySelector(".twin__why");
    if (twin.why_match) {
      why.textContent = twin.why_match;
    } else {
      why.textContent = "No summary available — open the profile for details.";
      why.classList.add("twin__why--empty");
    }

    const highlightsEl = li.querySelector(".twin__highlights");
    (twin.highlights || []).slice(0, 2).forEach((h) => {
      const div = document.createElement("div");
      div.className = "twin__highlight";
      div.textContent = h.length > 220 ? h.slice(0, 220).trim() + "…" : h;
      highlightsEl.appendChild(div);
    });

    const linkedinLink = li.querySelector(".twin__linkedin");
    linkedinLink.href = twin.linkedin_url;

    list.appendChild(li);
  });

  $("#results-meta").textContent = formatMeta(data);
  $("#results").classList.remove("hidden");
  $("#results").scrollIntoView({ behavior: "smooth", block: "start" });
}

function formatMeta(data) {
  const bits = [`${data.twins.length} twins`];
  if (data.from_cache) {
    bits.push("from cache");
  } else {
    bits.push(`${(data.duration_ms / 1000).toFixed(1)}s`);
  }
  return bits.join(" · ");
}

// ---------- ui helpers ----------
function setLoading(loading) {
  const btn = $("#submit");
  btn.disabled = loading;
  btn.querySelector(".cta__label").textContent = loading ? "Searching…" : "Find my twins";
  $("#status").classList.toggle("hidden", !loading);
  if (loading) hideResults();
}

function showError(msg) {
  const el = $("#error");
  el.textContent = msg;
  el.classList.remove("hidden");
}

function hideError() {
  $("#error").classList.add("hidden");
}

function hideResults() {
  $("#results").classList.add("hidden");
}
