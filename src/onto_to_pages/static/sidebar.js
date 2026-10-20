(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var sections = document.querySelectorAll(".toc-section");
    var masterToggle = document.querySelector("[data-toc-toggle-all]");

    if (masterToggle && sections.length) {
      masterToggle.addEventListener("click", function () {
        var anyOpen = Array.prototype.some.call(sections, function (el) {
          return el.open;
        });
        var nextOpen = !anyOpen;
        Array.prototype.forEach.call(sections, function (el) {
          el.open = nextOpen;
        });
        masterToggle.textContent = nextOpen ? "Collapse all" : "Expand all";
      });
    }

    // Clicking the section heading link should navigate, not just toggle
    // the <details> open/closed (both would otherwise fire on one click).
    var sectionLinks = document.querySelectorAll(".toc-section-link");
    Array.prototype.forEach.call(sectionLinks, function (link) {
      link.addEventListener("click", function (e) {
        e.stopPropagation();
      });
    });
  });
})();
