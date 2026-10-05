"""A drop zone for pasted text that sends it to Python without displaying it.

A plain text area only reports its value once it loses focus, and it keeps
showing what was pasted. This one reads the clipboard on paste, so the
notebook updates right away, and stays empty.
"""

import anywidget
import traitlets

_ESM = """
function render({ model, el }) {
  const box = document.createElement("textarea");
  box.className = "paste-box";
  box.rows = 1;
  box.placeholder = model.get("placeholder");
  box.addEventListener("paste", (event) => {
    event.preventDefault();
    model.set("text", event.clipboardData.getData("text/plain"));
    model.save_changes();
    box.blur();
  });
  // Only pasting counts; anything typed or dropped is discarded.
  box.addEventListener("input", () => { box.value = ""; });
  el.appendChild(box);
}
export default { render };
"""

_CSS = """
.paste-box {
  box-sizing: border-box;
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px dashed var(--slate-8, #94a3b8);
  border-radius: 6px;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 0.85rem;
  resize: none;
  overflow: hidden;
}
.paste-box:focus {
  outline: none;
  border-style: solid;
  border-color: var(--blue-9, #3b82f6);
}
"""


class PasteBox(anywidget.AnyWidget):
    _esm = _ESM
    _css = _CSS
    placeholder = traitlets.Unicode("").tag(sync=True)
    text = traitlets.Unicode("").tag(sync=True)
