// Progressive enhancement for the /regione/<key> page: grows the score and
// movement bars and counts the scores up from zero when each block scrolls into
// view. The server already renders the final values, so no-JS readers and search
// engines see the real numbers; this only animates what is already on the page,
// and bails out entirely when the visitor prefers reduced motion.
(function () {
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Bars: remember their server-rendered width, then reset to 0 so they can grow.
  var bars = [];
  Array.prototype.forEach.call(
    document.querySelectorAll(".score-bar > span, .movement-bar > span"),
    function (span) {
      var target = span.style.width;
      if (!target) return;
      bars.push({ el: span, target: target });
    }
  );

  // Count-up targets: the theme-chip scores (whole element) and the theme-table
  // scores (the text node right after each .score-bar).
  var counters = [];
  function toInt(text) {
    var value = parseInt(String(text).replace(/[^0-9-]/g, ""), 10);
    return isFinite(value) ? value : null;
  }
  Array.prototype.forEach.call(document.querySelectorAll(".theme-chips li span"), function (el) {
    var end = toInt(el.textContent);
    if (end !== null) counters.push({ el: el, end: end });
  });
  Array.prototype.forEach.call(document.querySelectorAll(".profile-themes .score-bar"), function (bar) {
    var node = bar.nextSibling;
    while (node && node.nodeType === 3 && !node.textContent.trim()) node = node.nextSibling;
    if (node && node.nodeType === 3) {
      var end = toInt(node.textContent);
      if (end !== null) counters.push({ node: node, end: end });
    }
  });

  if (reduced || (!bars.length && !counters.length)) return;

  bars.forEach(function (b) { b.el.style.width = "0%"; });
  counters.forEach(function (c) { setText(c, "0"); });

  function setText(c, value) {
    if (c.node) c.node.textContent = value;
    else c.el.textContent = value;
  }

  function animateCounter(c) {
    var start = performance.now();
    var duration = 800;
    function tick(now) {
      var t = Math.min(1, (now - start) / duration);
      var eased = 1 - Math.pow(1 - t, 3);
      setText(c, String(Math.round(c.end * eased)));
      if (t < 1) requestAnimationFrame(tick);
      else setText(c, String(c.end));
    }
    requestAnimationFrame(tick);
  }

  function reveal(root) {
    bars.forEach(function (b) {
      if (root === document || root.contains(b.el)) b.el.style.width = b.target;
    });
    counters.forEach(function (c) {
      var el = c.node ? c.node.parentNode : c.el;
      if (root === document || root.contains(el)) animateCounter(c);
    });
  }

  var blocks = Array.prototype.slice.call(
    document.querySelectorAll(".profile-cols, .profile-movement, .profile-themes")
  );
  if (!("IntersectionObserver" in window) || !blocks.length) {
    reveal(document);
    return;
  }
  var io = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          reveal(entry.target);
          io.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.2 }
  );
  blocks.forEach(function (block) { io.observe(block); });
})();
