// Lesson tree: tracks → lessons in order, then the units with the lessons that use them.

import type { LessonEntry, LessonIndex, UnitEntry } from './api';

export interface TreeHandlers {
  lesson(lesson: LessonEntry): void;
  unit(unit: UnitEntry): void;
}

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className?: string, text?: string): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export class LessonTree {
  private selected: HTMLElement | null = null;

  constructor(private readonly host: HTMLElement, private readonly handlers: TreeHandlers) {}

  render(index: LessonIndex, selectedLesson?: string): void {
    this.host.replaceChildren();
    this.selected = null;
    const titles = new Map<string, string>();
    for (const track of index.tracks) for (const l of track.lessons) titles.set(l.id, l.title);

    if (index.problems.length) {
      const box = el('div', 'problems');
      box.append(el('strong', undefined, '레슨 manifest 오류'));
      for (const p of index.problems) box.append(el('div', 'mono', p));
      this.host.append(box);
    }

    for (const track of index.tracks) {
      const group = el('details', 'track');
      group.open = true;
      const summary = el('summary', undefined, track.title);
      summary.title = track.summary;
      group.append(summary);
      for (const lesson of track.lessons) {
        const item = el('button', 'tree-item lesson');
        item.dataset.lesson = lesson.id;
        item.append(el('span', 'name', lesson.title));
        if (lesson.run.profile === 'long') item.append(el('span', 'badge', 'long'));
        item.title = `${lesson.summary}\n${lesson.path}`;
        item.addEventListener('click', () => {
          this.select(item);
          this.handlers.lesson(lesson);
        });
        group.append(item);
        if (lesson.id === selectedLesson) this.select(item);
      }
      this.host.append(group);
    }

    const units = el('details', 'track units');
    units.open = true;
    units.append(el('summary', undefined, '유닛'));
    for (const unit of index.units) {
      const item = el('button', 'tree-item unit');
      item.dataset.unit = unit.id;
      item.append(el('span', 'name', unit.title));
      const used = unit.usedBy.map((id) => titles.get(id) ?? id);
      item.append(el('span', 'used-by', used.length ? `사용: ${unit.usedBy.join(', ')}` : '사용하는 레슨 없음'));
      item.title = `${unit.summary}\n사용하는 레슨: ${used.join(' / ') || '없음'}`;
      item.addEventListener('click', () => {
        this.select(item);
        this.handlers.unit(unit);
      });
      units.append(item);
    }
    this.host.append(units);
  }

  private select(item: HTMLElement): void {
    this.selected?.classList.remove('selected');
    this.selected = item;
    item.classList.add('selected');
  }
}
