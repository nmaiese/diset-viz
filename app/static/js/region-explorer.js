// Client-side filtering and sorting for the per-region indicator explorer.
// Pure vanilla JS; the table rows are already server-rendered (good for SEO and
// no-JS readers), this only shows/hides and reorders them based on the controls.
(function () {
  var section = document.getElementById("explorer");
  var table = document.getElementById("explorer-table");
  if (!section || !table) return;

  var tbody = table.querySelector("tbody");
  var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr"));
  var search = document.getElementById("explorer-search");
  var themeSel = document.getElementById("explorer-theme");
  var strengthSel = document.getElementById("explorer-strength");
  var sortSel = document.getElementById("explorer-sort");
  var shown = document.getElementById("explorer-shown");
  var empty = document.getElementById("explorer-empty");
  var pills = Array.prototype.slice.call(section.querySelectorAll(".macro-pill"));

  var state = { macro: "", theme: "", strength: "", q: "", sort: "rank" };

  function num(row, attr) {
    var raw = row.getAttribute(attr);
    return raw === "" || raw === null ? null : parseFloat(raw);
  }

  function matches(row) {
    if (state.macro && row.getAttribute("data-macro") !== state.macro) return false;
    if (state.theme && row.getAttribute("data-theme") !== state.theme) return false;
    if (state.q && row.getAttribute("data-name").indexOf(state.q) === -1) return false;
    if (state.strength) {
      var score = num(row, "data-score");
      if (state.strength === "context" && score !== null) return false;
      if (state.strength === "strong" && !(score !== null && score >= 70)) return false;
      if (state.strength === "weak" && !(score !== null && score <= 30)) return false;
    }
    return true;
  }

  // Sort comparators. Nulls always sink to the bottom so empty cells never lead.
  function compare(a, b) {
    if (state.sort === "az") {
      return a.getAttribute("data-name").localeCompare(b.getAttribute("data-name"));
    }
    if (state.sort === "theme") {
      var ta = a.getAttribute("data-theme"), tb = b.getAttribute("data-theme");
      return ta.localeCompare(tb) || a.getAttribute("data-name").localeCompare(b.getAttribute("data-name"));
    }
    if (state.sort === "movement") {
      return rankNull(num(b, "data-movement")) - rankNull(num(a, "data-movement"));
    }
    // rank: 1 (best) first, nulls last
    var ra = num(a, "data-rank"), rb = num(b, "data-rank");
    if (ra === null && rb === null) return 0;
    if (ra === null) return 1;
    if (rb === null) return -1;
    return ra - rb;
  }

  function rankNull(value) {
    return value === null ? -Infinity : value;
  }

  function apply() {
    var visible = rows.filter(matches);
    visible.sort(compare);
    var frag = document.createDocumentFragment();
    visible.forEach(function (row) { frag.appendChild(row); });
    rows.forEach(function (row) { if (matches(row) === false) row.hidden = true; });
    visible.forEach(function (row) { row.hidden = false; });
    tbody.appendChild(frag);
    shown.textContent = visible.length;
    if (empty) empty.hidden = visible.length !== 0;
  }

  pills.forEach(function (pill) {
    pill.addEventListener("click", function () {
      pills.forEach(function (p) { p.classList.remove("is-active"); });
      pill.classList.add("is-active");
      state.macro = pill.getAttribute("data-macro") || "";
      apply();
    });
  });
  if (search) search.addEventListener("input", function () {
    state.q = search.value.trim().toLowerCase();
    apply();
  });
  if (themeSel) themeSel.addEventListener("change", function () { state.theme = themeSel.value; apply(); });
  if (strengthSel) strengthSel.addEventListener("change", function () { state.strength = strengthSel.value; apply(); });
  if (sortSel) sortSel.addEventListener("change", function () { state.sort = sortSel.value; apply(); });

  apply();
})();
