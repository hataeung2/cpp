// Lesson tree: tracks → lessons in order, then the units with the lessons that use them.

import type { LessonEntry, LessonIndex, UnitEntry } from './api';
import { localized, t } from './i18n';
import { lessonHaystack, matches, queryTerms, unitHaystack } from './search';

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
  private selectedKey: string | null = null;
  private rememberedLesson: string | null = null;
  private collapsed = new Set<string>();
  private firstLesson: LessonEntry | null = null;

  constructor(private readonly host: HTMLElement, private readonly handlers: TreeHandlers) {}

  firstVisibleLesson(): LessonEntry | null {
    return this.firstLesson;
  }

  /** The page opened this lesson without a tree click (Enter in the search box): highlight it from the next render. */
  markLesson(id: string): void {
    this.rememberedLesson = id;
    this.selectedKey = `lesson:${id}`;
  }

  render(index: LessonIndex, selectedLesson?: string, query = ''): { lessons: number; units: number } {
    this.firstLesson = null;
    this.host.replaceChildren();
    this.selected = null;

    if (selectedLesson && selectedLesson !== this.rememberedLesson) {
      this.rememberedLesson = selectedLesson;
      this.selectedKey = `lesson:${selectedLesson}`;
    }

    const titles = new Map<string, string>();
    for (const track of index.tracks) {
      for (const l of track.lessons) {
        titles.set(l.id, localized(l.title, l.titleEn).text);
      }
    }

    if (index.problems.length) {
      const box = el('div', 'problems');
      box.append(el('strong', undefined, t('tree.manifestProblems')));
      for (const p of index.problems) box.append(el('div', 'mono', p));
      this.host.append(box);
    }

    let visibleLessons = 0;
    let visibleUnits = 0;
    const hasTerms = queryTerms(query).length > 0;

    for (const track of index.tracks) {
      const visibleTrackLessons: LessonEntry[] = [];
      for (const lesson of track.lessons) {
        const haystack = lessonHaystack(lesson, track, index.tags ?? {});
        if (matches(haystack, query)) {
          visibleTrackLessons.push(lesson);
        }
      }
      if (visibleTrackLessons.length === 0) {
        continue;
      }

      const group = el('details', 'track');
      group.open = hasTerms ? true : !this.collapsed.has(track.id);
      group.addEventListener('toggle', () => {
        // toggle fires after render returns: ignore forced opening (query) and groups a later render replaced
        if (hasTerms || !group.isConnected) return;
        if (group.open) {
          this.collapsed.delete(track.id);
        } else {
          this.collapsed.add(track.id);
        }
      });

      const trackTitle = localized(track.title, track.titleEn);
      const summary = el('summary', undefined, trackTitle.text);
      if (trackTitle.fallback) summary.classList.add('fallback');
      const trackSummary = localized(track.summary, track.summaryEn);
      summary.title = trackSummary.text;
      group.append(summary);

      for (const lesson of visibleTrackLessons) {
        visibleLessons++;
        if (!this.firstLesson) {
          this.firstLesson = lesson;
        }
        const item = el('button', 'tree-item lesson');
        item.dataset.lesson = lesson.id;
        const lessonTitle = localized(lesson.title, lesson.titleEn);
        const name = el('span', 'name', lessonTitle.text);
        if (lessonTitle.fallback) name.classList.add('fallback');
        item.append(name);
        if (lesson.run.profile === 'long') item.append(el('span', 'badge', 'long'));
        const lessonSummary = localized(lesson.summary, lesson.summaryEn);
        item.title = `${lessonSummary.text}\n${lesson.path}`;
        item.addEventListener('click', () => {
          this.rememberedLesson = lesson.id;
          this.select(`lesson:${lesson.id}`, item);
          this.handlers.lesson(lesson);
        });
        group.append(item);
        if (`lesson:${lesson.id}` === this.selectedKey) {
          this.select(`lesson:${lesson.id}`, item);
        }
      }
      this.host.append(group);
    }

    const visibleUnitsList: UnitEntry[] = [];
    for (const unit of index.units) {
      const haystack = unitHaystack(unit);
      if (matches(haystack, query)) {
        visibleUnitsList.push(unit);
      }
    }

    if (visibleUnitsList.length > 0) {
      const units = el('details', 'track units');
      units.open = hasTerms ? true : !this.collapsed.has('__units');
      units.addEventListener('toggle', () => {
        if (hasTerms || !units.isConnected) return;
        if (units.open) {
          this.collapsed.delete('__units');
        } else {
          this.collapsed.add('__units');
        }
      });
      units.append(el('summary', undefined, t('tree.units')));

      for (const unit of visibleUnitsList) {
        visibleUnits++;
        const item = el('button', 'tree-item unit');
        item.dataset.unit = unit.id;
        const unitTitle = localized(unit.title, unit.titleEn);
        const name = el('span', 'name', unitTitle.text);
        if (unitTitle.fallback) name.classList.add('fallback');
        item.append(name);
        const used = unit.usedBy.map((id) => titles.get(id) ?? id);
        item.append(
          el(
            'span',
            'used-by',
            unit.usedBy.length ? t('tree.usedBy', { ids: unit.usedBy.join(', ') }) : t('tree.usedByNone'),
          ),
        );
        const unitSummary = localized(unit.summary, unit.summaryEn);
        const lessons = used.length ? used.join(' / ') : t('tree.none');
        item.title = `${unitSummary.text}\n${t('tree.unitTooltip', { lessons })}`;
        item.addEventListener('click', () => {
          this.select(`unit:${unit.id}`, item);
          this.handlers.unit(unit);
        });
        units.append(item);
        if (`unit:${unit.id}` === this.selectedKey) {
          this.select(`unit:${unit.id}`, item);
        }
      }
      this.host.append(units);
    }

    if (visibleLessons === 0 && visibleUnits === 0 && hasTerms) {
      this.host.append(el('p', 'muted tree-empty', t('search.noResults')));
    }

    return { lessons: visibleLessons, units: visibleUnits };
  }

  private select(key: string, item: HTMLElement): void {
    this.selected?.classList.remove('selected');
    this.selected = item;
    this.selectedKey = key;
    item.classList.add('selected');
  }
}
