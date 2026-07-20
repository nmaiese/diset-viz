// Progressive enhancement for the /regione/<key> page: reveals bars without
// changing layout. Numeric text stays at the server-rendered final value, so it
// never causes reflow or scroll jumps.
(function () {
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (reduced) return;

  var bars = Array.prototype.slice.call(
    document.querySelectorAll(".score-bar > span, .movement-bar > span")
  );
  if (!bars.length) return;

  bars.forEach(function (span) {
    span.style.transformOrigin = "left center";
    span.style.transform = "scaleX(0)";
  });

  function reveal(root) {
    bars.forEach(function (bar) {
      if (root === document || root.contains(bar)) bar.style.transform = "scaleX(1)";
    });
  }

  var blocks = Array.prototype.slice.call(
    document.querySelectorAll(".profile-quad, .profile-themes")
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
