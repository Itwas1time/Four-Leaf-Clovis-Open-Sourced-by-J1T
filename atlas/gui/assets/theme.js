/* Appearance is local to this browser. It never enters Dash or saved research. */
(function () {
    "use strict";
    var key = "clovis-theme";
    var theme = "light";
    try { if (window.localStorage.getItem(key) === "dark") theme = "dark"; } catch (_) {}
    function sync() {
        if (document.body) document.body.dataset.clovisTheme = theme;
        var button = document.getElementById("clovis-theme-toggle");
        if (button) {
            var dark = theme === "dark";
            var label = dark ? "Light" : "Dark";
            if (button.textContent !== label) button.textContent = label;
            if (button.getAttribute("aria-pressed") !== String(dark)) button.setAttribute("aria-pressed", String(dark));
            button.setAttribute("aria-label", "Dark appearance");
            button.title = "Switch to " + (dark ? "light" : "dark") + " appearance";
        }
    }
    // Assets can execute before the body and before Dash mounts its controls.
    sync();
    document.addEventListener("DOMContentLoaded", sync, {once: true});
    new MutationObserver(function (records) {
        if (records.some(function (record) { return record.addedNodes.length; })) sync();
    }).observe(document.documentElement, {childList: true, subtree: true});
    document.addEventListener("click", function (event) {
        if (!(event.target instanceof Element) || !event.target.closest("#clovis-theme-toggle")) return;
        theme = theme === "dark" ? "light" : "dark";
        try { window.localStorage.setItem(key, theme); } catch (_) {}
        sync();
    });
    window.addEventListener("storage", function (event) {
        if (event.key === key || event.key === null) {
            theme = event.newValue === "dark" ? "dark" : "light";
            sync();
        }
    });
}());
