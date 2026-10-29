// ruleid: dom-append-may-print-null
box.append(h("span", {}, text), when ? h("span", {}, when) : null);
// ruleid: dom-append-may-print-null
main.prepend(isOpen && banner);
// ruleid: dom-append-may-print-null
row.after(empty ? null : note);
// ok: dom-append-may-print-null
box.append(...[h("span", {}, text), when ? h("span", {}, when) : null].filter(Boolean));
// ok: dom-append-may-print-null
box.append(h("div", {}, when ? h("span", {}, when) : null));
// ok: dom-append-may-print-null
list.push(when ? a : null);
