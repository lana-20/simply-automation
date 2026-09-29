(function () {
  var root = document.documentElement;

  // Theme toggle: cycles to the opposite of what is currently showing and remembers it.
  var toggle = document.getElementById("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var current = root.getAttribute("data-theme") ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      var next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("sa-theme", next); } catch (e) {}
    });
  }

  // Reading progress along the gold rule under the top bar.
  var bar = document.getElementById("progress");
  var article = document.querySelector(".prose");
  if (bar && article) {
    var update = function () {
      var rect = article.getBoundingClientRect();
      var total = rect.height - window.innerHeight;
      var pct = total > 0 ? Math.min(1, Math.max(0, -rect.top / total)) : 1;
      bar.style.width = (pct * 100).toFixed(2) + "%";
    };
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    update();
  }

  // Highlight the current section in the side rail.
  var links = document.querySelectorAll(".rail-list a");
  if (links.length && "IntersectionObserver" in window) {
    var byId = {};
    links.forEach(function (a) { byId[a.getAttribute("href").slice(1)] = a; });
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        links.forEach(function (a) { a.classList.remove("is-current"); });
        var link = byId[entry.target.id];
        if (link) link.classList.add("is-current");
      });
    }, { rootMargin: "0px 0px -75% 0px" });
    Object.keys(byId).forEach(function (id) {
      var el = document.getElementById(id);
      if (el) observer.observe(el);
    });
  }
})();
