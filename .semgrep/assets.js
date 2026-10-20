// ruleid: no-hardcoded-server
const BASE = "http://192.168.1.80:8188";
// ok: no-hardcoded-server
const cfg = await fetchJson(base + "assets.config.json");
// ruleid: asset-by-slot-id
img.src = "../assets/comfyui/emblems/emblem-flat-coach-s11.png";
// ok: asset-by-slot-id
img.src = assets.url("emblem.learning");
