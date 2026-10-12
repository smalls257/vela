// ruleid: prototype-no-hardcoded-server
const BASE = "http://192.168.1.80:8188";
// ok: prototype-no-hardcoded-server
const cfg = await fetchJson(base + "assets.config.json");
// ruleid: prototype-asset-by-slot-id
img.src = "../gallery/assets/comfyui/emblems/emblem-flat-coach-s11.png";
// ok: prototype-asset-by-slot-id
img.src = assets.url("emblem.coach");
