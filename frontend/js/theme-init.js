// Applies the last-known theme before first paint. The saved setting in the
// database stays authoritative; this cached copy only avoids a flash.
(function () {
  try {
    var theme = localStorage.getItem("fet-theme");
    if (theme === "light" || theme === "dark") document.documentElement.dataset.theme = theme;
    if (localStorage.getItem("fet-sidebar") === "collapsed") document.documentElement.classList.add("sidebar-collapsed");
  } catch (error) { /* storage unavailable */ }
})();
