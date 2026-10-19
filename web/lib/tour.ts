// Guided demo state (U15). Flags live in sessionStorage so the tour bar and the pages can share them; a window
// event tells the bar when one changes. Nothing here calls the API.
export const tourGet = (k: string): string => {
  try { return sessionStorage.getItem(`tour-${k}`) ?? ""; } catch { return ""; }
};
export const tourSet = (k: string, v = "1") => {
  try { sessionStorage.setItem(`tour-${k}`, v); } catch { /* storage blocked: the tour just shows fewer cues */ }
  window.dispatchEvent(new Event("tour-state"));
};
export const tourClear = () => {
  try { ["issued", "record", "marked", "queued"].forEach((k) => sessionStorage.removeItem(`tour-${k}`)); } catch { /* ignore */ }
  window.dispatchEvent(new Event("tour-state"));
};
