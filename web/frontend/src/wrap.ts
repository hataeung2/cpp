// Line-wrap choices of the editor and the Output panel (spec 070-19 Assumptions 3 and 4).
// Wrapping is on unless the stored choice says off; blocked storage keeps the default.

export const EDITOR_WRAP_KEY = 'atugcc.wrap.editor';
export const OUTPUT_WRAP_KEY = 'atugcc.wrap.output';

export function loadWrap(key: string): boolean {
  try {
    return localStorage.getItem(key) !== 'off';
  } catch {
    return true;
  }
}

export function saveWrap(key: string, on: boolean): void {
  try {
    localStorage.setItem(key, on ? 'on' : 'off');
  } catch {
    // blocked storage: the choice lasts until the page closes
  }
}
