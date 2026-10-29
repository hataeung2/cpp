// AC-8: every Mermaid part the seed lessons produce parses. The fixture holds the parts a real
// run wrote (web/server/capture_diagrams.py); refresh it after changing a lesson or the generator.
import mermaid from 'mermaid';
import { beforeAll, describe, expect, it } from 'vitest';
import { mermaidConfig, mermaidSource } from '../src/diagrams';
import fixture from './fixtures/seed_diagrams.json';

interface Part {
  lesson: string;
  tracer: number;
  part: number;
  diagram: string;
  title: string;
  source: string;
}
const parts = (fixture as { parts: Part[] }).parts;

describe('seed lesson diagrams', () => {
  beforeAll(() => mermaid.initialize(mermaidConfig(false)));

  it('has parts from the seed lessons', () => {
    expect(parts.length).toBeGreaterThan(0);
    for (const p of parts) expect(['sequence', 'state', 'structure']).toContain(p.diagram);
  });

  it.each(parts.map((p) => [`${p.lesson} tracer ${p.tracer} ${p.title} #${p.part}`, p] as const))('%s parses', async (_, part) => {
    await expect(mermaid.parse(mermaidSource(part.source))).resolves.toBeTruthy();
  });

  it('renders at natural width with 14 px text (diagrams.md §3)', () => {
    const config = mermaidConfig(false);
    expect([config.flowchart, config.sequence, config.state, config.class].every((c) => c.useMaxWidth === false)).toBe(true);
    expect(config.fontSize).toBeGreaterThanOrEqual(14);
  });

  it('rejects a broken part (the check can fail)', async () => {
    await expect(mermaid.parse('stateDiagram-v2\n    A --> --> B')).rejects.toBeTruthy();
  });

  it('rejects the fenced source as is (mermaidSource is needed)', async () => {
    await expect(mermaid.parse(parts[0].source)).rejects.toBeTruthy();
  });
});
