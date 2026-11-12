// Step-by-step diagram replay (spec 070-07): which events are steps, how the cursor moves, how a
// fetched part list is folded. No DOM here; DiagramsPanel draws, the tests cover this file.

import type { DiagramLine, DoneData, TraceEvent } from './api';

export const REPLAY_DEBOUNCE_MS = 150;

const STEP_KINDS = new Set(['message', 'transition', 'node']);

/** Why a tracer cannot be replayed: more events than the server keeps, or the Events tab lost some. */
export type ReplayOff = 'tooMany' | 'truncated';

export interface ReplayTracer {
  tracer: number;
  /** events of this tracer in seq order (empty when `off`) */
  steps: TraceEvent[];
  /** events the run produced for this tracer (done.replay.tracers) */
  count: number;
  off: ReplayOff | null;
}

/** Tracers of a finished run with their steps. `events` is what the Events tab holds (any order). */
export function replayTracers(done: DoneData, events: readonly TraceEvent[]): ReplayTracer[] {
  const info = done.replay;
  if (!info) return [];
  const result: ReplayTracer[] = [];
  for (const [key, count] of Object.entries(info.tracers)) {
    const tracer = Number(key);
    if (!Number.isInteger(tracer) || count <= 0) continue;
    const steps = events
      .filter((e) => e.tracer === tracer && STEP_KINDS.has(e.kind))
      .sort((a, b) => a.seq - b.seq);
    const off: ReplayOff | null = count > info.max ? 'tooMany' : steps.length < count ? 'truncated' : null;
    result.push({ tracer, steps: off ? [] : steps, count, off });
  }
  return result.sort((a, b) => a.tracer - b.tracer);
}

/** Where the replay cursor is; one object per finished run. */
export class ReplayState {
  readonly playable: ReplayTracer[];
  readonly unavailable: ReplayTracer[];
  active = false;
  private tracerIndex = 0;
  private stepIndex = 0;

  constructor(all: readonly ReplayTracer[]) {
    this.playable = all.filter((t) => t.off === null && t.steps.length > 0);
    this.unavailable = all.filter((t) => t.off !== null);
  }

  get available(): boolean {
    return this.playable.length > 0;
  }

  /** The tracer and event under the cursor; null when the replay is off or nothing can be replayed. */
  get current(): { tracer: number; event: TraceEvent; index: number; total: number } | null {
    if (!this.active || !this.available) return null;
    const t = this.playable[this.tracerIndex];
    return { tracer: t.tracer, event: t.steps[this.stepIndex], index: this.stepIndex, total: t.steps.length };
  }

  /** Switch on (at the last step, the finished diagram) or off. */
  setActive(on: boolean): void {
    this.active = on && this.available;
    if (this.active) this.stepIndex = this.playable[this.tracerIndex].steps.length - 1;
  }

  selectTracer(tracer: number): boolean {
    const at = this.playable.findIndex((t) => t.tracer === tracer);
    if (at < 0) return false;
    this.tracerIndex = at;
    this.stepIndex = this.playable[at].steps.length - 1;
    return true;
  }

  /** Move to step `index` (clamped); true when the cursor moved. */
  setStep(index: number): boolean {
    if (!this.active) return false;
    const last = this.playable[this.tracerIndex].steps.length - 1;
    const next = Math.min(Math.max(0, Math.trunc(index)), last);
    const moved = next !== this.stepIndex;
    this.stepIndex = next;
    return moved;
  }

  first(): boolean {
    return this.setStep(0);
  }
  prev(): boolean {
    return this.setStep(this.stepIndex - 1);
  }
  next(): boolean {
    return this.setStep(this.stepIndex + 1);
  }
  last(): boolean {
    return this.setStep(Number.MAX_SAFE_INTEGER);
  }

  /** Put the cursor on the event with this seq (an Events row was clicked); false when no tracer has it. */
  goToSeq(seq: number): boolean {
    if (!this.active) return false;
    for (let t = 0; t < this.playable.length; t++) {
      const at = this.playable[t].steps.findIndex((e) => e.seq === seq);
      if (at >= 0) {
        this.tracerIndex = t;
        this.stepIndex = at;
        return true;
      }
    }
    return false;
  }
}

/** Per part of a fetched replay: fold it? Earlier Sequence parts fold, the part with the cursor stays open (Assumption 11). */
export function foldedParts(parts: readonly DiagramLine[]): boolean[] {
  return parts.map((p) => p.diagram === 'sequence' && p.part < p.parts - 1);
}

/** Fetched replay diagrams by (tracer, seq), so stepping back and forth asks the server once. */
export class ReplayCache {
  private readonly map = new Map<string, DiagramLine[]>();

  get(tracer: number, seq: number): DiagramLine[] | undefined {
    return this.map.get(`${tracer}:${seq}`);
  }

  set(tracer: number, seq: number, parts: DiagramLine[]): void {
    this.map.set(`${tracer}:${seq}`, parts);
  }

  clear(): void {
    this.map.clear();
  }
}
