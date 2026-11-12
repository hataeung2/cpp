// KI-051: a class a panel div carries (`<div class="panel exercises">`) must not get `display` from a
// bare `.class` rule in theme.css: it would override `.panel { display: none }` and show the panel on every tab.
// @ts-ignore
import fs from 'node:fs';
// @ts-ignore
import path from 'node:path';
// @ts-ignore
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const frontendDir = path.resolve(fileURLToPath(import.meta.url), '../..');
const html: string = fs.readFileSync(path.join(frontendDir, 'index.html'), 'utf8');
const css: string = (fs.readFileSync(path.join(frontendDir, 'src/theme.css'), 'utf8') as string).replace(/\/\*[\s\S]*?\*\//g, '');

describe('panel classes in theme.css', () => {
  const panelClasses = new Set<string>();
  for (const m of html.matchAll(/<div id="panel-[a-z]+" class="([^"]*)"/g)) {
    for (const c of m[1].split(/\s+/)) if (c && c !== 'panel' && c !== 'active') panelClasses.add(c);
  }

  it('finds the panel divs of index.html', () => {
    expect([...panelClasses]).toContain('exercises');
  });

  it.each([...panelClasses])('no bare .%s rule sets display (it would beat .panel{display:none})', (cls) => {
    for (const m of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      const selectors = m[1].split(',').map((s) => s.trim());
      if (selectors.includes(`.${cls}`)) expect(m[2], `rule for .${cls}`).not.toMatch(/(^|[;\s])display\s*:/);
    }
  });
});
