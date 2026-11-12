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

// 070-07 AC-3: the highlight the C++ generator adds for the last event (DiagramRange::markLast) must parse.
// The sources are the exact text of mermaid_formatter.hpp; tests/pattern/test_diagram_range.cpp checks that the
// C++ side produces them. Rendering is checked in a real browser (testrecord), not here (no DOM in vitest).
describe('marked diagrams (070-07)', () => {
  const marked: Record<string, string> = {
    sequence: 'sequenceDiagram\n    A->>B:x\n    rect rgba(255, 235, 59, 0.35)\n        B->>C:y ×2\n    end\n',
    state: 'stateDiagram-v2\n    A --> B : t\n    B --> C : u\n    classDef current fill:#fff3b0,stroke:#e0a800,color:#000\n    class C current\n',
    structure: 'classDiagram\n    Root --> A : contains\n    A --> B : contains\n    style B fill:#fff3b0,stroke:#e0a800,color:#000\n',
  };
  beforeAll(() => mermaid.initialize(mermaidConfig(false)));

  it.each(Object.entries(marked))('%s with the last event marked parses', async (_, source) => {
    await expect(mermaid.parse(source)).resolves.toBeTruthy();
  });

  // `linkStyle 1 stroke:#e0a800` parses in a classDiagram, but only as a class named "linkStyle1stroke" (seen
  // in the browser render, 070-07 testrecord): parse success proves nothing there, so the generator uses `style`.
  it('a classDiagram linkStyle with two properties is a parse error', async () => {
    await expect(mermaid.parse('classDiagram\n    A --> B : x\n    linkStyle 0 stroke:#e0a800,stroke-width:3px\n')).rejects.toBeTruthy();
  });

  it('a quoted state id cannot be classed (why the C++ side skips it)', async () => {
    await expect(mermaid.parse('stateDiagram-v2\n    A --> "b c" : t\n    classDef current fill:#fff3b0\n    class "b c" current\n')).rejects.toBeTruthy();
  });
});
