// Send the selected local JSON file to the comparison store.
document.addEventListener("change", function (event) {
    const input = event.target;
    if (!input.matches || !input.matches("#candidate-upload input[type=file]")) return;
    const file = input.files && input.files[0];
    if (!file) return;

    const send = (data) => window.dash_clientside.set_props("candidate-file-store", {data});
    if (file.size > 1000000) {
        send({filename: file.name, error: "Candidate file is too large; use at most 1 MB of JSON."});
        input.value = "";
        return;
    }

    const reader = new FileReader();
    reader.onload = function () {
        send({filename: file.name, text: String(reader.result || "")});
        input.value = "";
    };
    reader.onerror = function () {
        send({filename: file.name, error: "The browser could not read this file."});
        input.value = "";
    };
    reader.readAsText(file);
});
