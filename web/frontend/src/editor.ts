// Editor area: Monaco with one tab per file (spec 070-02 §2.3).
// Files are the repository's own files: saving writes them (lessons/ only), and the sha of the
// version the tab started from detects edits made elsewhere (VS Code) as a conflict.

import 'monaco-editor/editor/editor.main';
import * as monaco from 'monaco-editor/editor/editor.api';
import EditorWorker from 'monaco-editor/editor/editor.worker?worker';
import { api, type Diagnostic } from './api';
import { groupByFile, toMarkers } from './diagnostics';
import { t } from './i18n';
import type { FileState } from './practice';

(self as unknown as { MonacoEnvironment: monaco.Environment }).MonacoEnvironment = {
  getWorker: () => new EditorWorker(),
};

interface Tab {
  path: string;
  model: monaco.editor.ITextModel | null; // loaded on first activation
  sha: string | null;
  writable: boolean;
  savedVersion: number;
  conflict: boolean;
  view: monaco.editor.ICodeEditorViewState | null;
  button: HTMLButtonElement;
}

export type ConflictChoice = 'reload' | 'overwrite' | 'cancel';

function languageOf(path: string): string {
  if (/\.(c|cc|cpp|cppm|cxx|h|hh|hpp|hxx|ipp|inl)$/i.test(path)) return 'cpp';
  if (/\.md$/i.test(path)) return 'markdown';
  if (/\.toml$/i.test(path)) return 'ini';
  return 'plaintext';
}

const baseName = (path: string) => path.slice(path.lastIndexOf('/') + 1);

export class EditorArea {
  private readonly editor: monaco.editor.IStandaloneCodeEditor;
  private readonly tabs = new Map<string, Tab>();
  private active: Tab | null = null;
  private diagnostics = new Map<string, Diagnostic[]>();
  private inline = new Map<string, Map<number, string>>(); // file -> line -> text after the line
  private readonly highlight: monaco.editor.IEditorDecorationsCollection;
  // Editor-owned, like `highlight`: Monaco did not render injected text of model-level decorations.
  private readonly inlineTimes: monaco.editor.IEditorDecorationsCollection;
  private readonly inlineStyle: HTMLStyleElement;
  private originalWritable = true;
  private practiceStates = new Map<string, FileState>();
  /** Called after a file is saved, so other views (README) can refresh. */
  onSaved: (path: string) => void = () => {};
  /** Called when the active tab changes (spec 070-16). */
  onActiveChange: (path: string | null) => void = () => {};

  constructor(
    host: HTMLElement,
    private readonly tabBar: HTMLElement,
    private readonly askConflict: (path: string, deleted: boolean) => Promise<ConflictChoice>,
    private readonly notify: (message: string) => void,
  ) {
    this.editor = monaco.editor.create(host, {
      automaticLayout: true,
      fontSize: 14,
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      tabSize: 4,
      renderWhitespace: 'selection',
    });
    this.highlight = this.editor.createDecorationsCollection();
    this.inlineTimes = this.editor.createDecorationsCollection();
    this.inlineStyle = document.head.appendChild(document.createElement('style'));
    this.editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      if (this.active) void this.save(this.active);
    });
    this.editor.onDidChangeModelContent(() => {
      if (this.active) this.renderTab(this.active);
    });
    window.addEventListener('focus', () => void this.refreshFromDisk());
  }

  setTheme(dark: boolean): void {
    monaco.editor.setTheme(dark ? 'vs-dark' : 'vs');
  }

  /** Replace the tab set; modified tabs of other files stay open, so no edit is lost. */
  showFiles(paths: string[], activate?: string): void {
    for (const tab of [...this.tabs.values()]) {
      if (!paths.includes(tab.path) && !this.isDirty(tab)) this.closeTab(tab);
    }
    for (const path of paths) this.ensureTab(path);
    this.reorder(paths);
    const target = activate ?? paths[0];
    if (target) void this.open(target);
  }

  /** Open a file (adding a tab if needed) and optionally highlight one line. `focus: false` keeps the keyboard where it is (diagram replay). */
  async open(path: string, line?: number, focus = true): Promise<void> {
    const tab = this.ensureTab(path);
    try {
      await this.load(tab);
    } catch (err) {
      this.notify(`${path}: ${(err as Error).message}`);
      return;
    }
    if (this.tabs.get(path) !== tab) {
      // the tab was closed (another lesson) while loading: free its model so the URI can be reused
      tab.model?.dispose();
      tab.model = null;
      return;
    }
    if (this.active && this.active !== tab) this.active.view = this.editor.saveViewState();
    this.active = tab;
    this.onActiveChange(tab.path);
    this.editor.setModel(tab.model);
    if (tab.view) this.editor.restoreViewState(tab.view);
    this.editor.updateOptions({ readOnly: !this.isWritable(tab) });
    this.renderInline();
    for (const t of this.tabs.values()) this.renderTab(t);
    this.highlight.clear();
    if (line !== undefined && tab.model) {
      const safe = Math.min(Math.max(1, line), tab.model.getLineCount());
      this.editor.revealLineInCenter(safe);
      this.editor.setPosition({ lineNumber: safe, column: 1 });
      this.highlight.set([{ range: new monaco.Range(safe, 1, safe, 1), options: { isWholeLine: true, className: 'line-highlight' } }]);
    }
    if (focus) this.editor.focus();
  }

  activePath(): string | null {
    return this.active?.path ?? null;
  }

  /** Lines currently highlighted (Events tab click), for checks and screenshots. */
  highlightedLines(): number[] {
    return this.highlight.getRanges().map((r) => r.startLineNumber);
  }

  /** Save every modified tab; false when the user cancelled a conflict. */
  async saveAll(): Promise<boolean> {
    for (const tab of this.tabs.values()) {
      if (this.isDirty(tab) && !(await this.save(tab))) return false;
    }
    return true;
  }

  /** Show build diagnostics as markers (replaces the previous run's). */
  setDiagnostics(list: Diagnostic[]): void {
    this.diagnostics = groupByFile(list);
    for (const tab of this.tabs.values()) this.applyMarkers(tab);
  }

  /** Text shown after source lines (span times, 070-06 §2.5); an empty map clears them. */
  setInlineTimings(byFile: Map<string, Map<number, string>>): void {
    this.inline = byFile;
    this.renderInline();
  }

  /**
   * Set whether original lesson files (lessons/...) are writable (spec 070-16).
   * In practice mode (false), every tab starting with lessons/ is treated as read-only.
   */
  setOriginalWritable(on: boolean): void {
    this.originalWritable = on;
    for (const tab of this.tabs.values()) this.renderTab(tab);
    if (this.active) {
      this.editor.updateOptions({ readOnly: !this.isWritable(this.active) });
    }
  }

  /** Store the latest file state map from practice status and re-render tabs (spec 070-16). */
  setPracticeStates(states: Map<string, FileState>): void {
    this.practiceStates = states;
    for (const tab of this.tabs.values()) this.renderTab(tab);
  }

  /**
   * Reload specified tabs from disk, discarding unsaved edits (spec 070-16).
   * Used after a reset; unloaded tabs are left untouched.
   */
  async reloadFromDisk(paths: string[]): Promise<void> {
    for (const path of paths) {
      const tab = this.tabs.get(path);
      if (!tab || !tab.model) continue;
      try {
        const file = await api.readFile(tab.path);
        tab.writable = file.writable;
        this.replaceContent(tab, file.content, file.sha);
        if (this.active === tab) {
          this.editor.updateOptions({ readOnly: !this.isWritable(tab) });
        }
      } catch (err) {
        this.notify(`${tab.path}: ${(err as Error).message}`);
      }
    }
  }

  /**
   * Open a Monaco diff editor comparing originPath and practicePath in host (spec 070-16).
   * Edits in the diff view modify the practice tab's model directly.
   * Returns a cleanup function that disposes the diff editor and original model only.
   */
  async openDiff(host: HTMLElement, originPath: string, practicePath: string): Promise<() => void> {
    const tab = this.ensureTab(practicePath);
    await this.load(tab);
    const originFile = await api.readFile(originPath);
    const originUri = monaco.Uri.from({
      scheme: 'origin',
      path: originPath.startsWith('/') ? originPath : '/' + originPath,
    });
    monaco.editor.getModel(originUri)?.dispose();
    const originModel = monaco.editor.createModel(originFile.content, languageOf(originPath), originUri);
    originModel.setEOL(monaco.editor.EndOfLineSequence.LF);

    const diffEditor = monaco.editor.createDiffEditor(host, {
      automaticLayout: true,
      readOnly: !this.isWritable(tab), // e.g. a copy's lesson.toml: shown, never saved
      originalEditable: false,
      renderSideBySide: true,
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      fontSize: 14,
    });
    diffEditor.setModel({
      original: originModel,
      modified: tab.model!,
    });
    const sub = tab.model!.onDidChangeContent(() => this.renderTab(tab));
    diffEditor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      void this.save(tab);
    });

    return () => {
      sub.dispose();
      diffEditor.dispose();
      originModel.dispose();
    };
  }

  // --- tabs ----------------------------------------------------------------------------
  private ensureTab(path: string): Tab {
    const existing = this.tabs.get(path);
    if (existing) return existing;
    const button = document.createElement('button');
    button.className = 'tab';
    button.setAttribute('role', 'tab');
    button.addEventListener('click', () => void this.open(path));
    this.tabBar.append(button);
    const tab: Tab = { path, model: null, sha: null, writable: false, savedVersion: 0, conflict: false, view: null, button };
    this.tabs.set(path, tab);
    this.renderTab(tab);
    return tab;
  }

  private reorder(paths: string[]): void {
    const rest = [...this.tabs.values()].filter((t) => !paths.includes(t.path));
    for (const tab of [...paths.map((p) => this.tabs.get(p)!), ...rest]) this.tabBar.append(tab.button);
  }

  private closeTab(tab: Tab): void {
    tab.button.remove();
    tab.model?.dispose();
    this.tabs.delete(tab.path);
    if (this.active === tab) {
      this.active = null;
      this.editor.setModel(null);
      this.onActiveChange(null);
    }
  }

  private renderTab(tab: Tab): void {
    const dirty = this.isDirty(tab);
    const readOnly = (!this.originalWritable && tab.path.startsWith('lessons/')) || (tab.model !== null && !tab.writable);
    const state = this.practiceStates.get(tab.path);
    const warnPrefix = state === 'both' ? '⚠ ' : '';
    const lockPrefix = readOnly ? '🔒 ' : '';
    tab.button.textContent = `${warnPrefix}${lockPrefix}${baseName(tab.path)}${dirty ? ' ●' : ''}`;
    tab.button.classList.toggle('active', tab === this.active);
    tab.button.classList.toggle('dirty', dirty);
    tab.button.classList.toggle('conflict', tab.conflict);
    tab.button.classList.toggle('practice-modified', state === 'modified' || state === 'both');
    tab.button.setAttribute('aria-selected', String(tab === this.active));
    if (tab.conflict) {
      tab.button.title = t('editor.changedOnDisk', { path: tab.path });
    } else if (state === 'both') {
      tab.button.title = `${tab.path}\n${t('practice.both')}`;
    } else if (state === 'modified') {
      tab.button.title = `${tab.path}\n${t('practice.modified')}`;
    } else if (!this.originalWritable && tab.path.startsWith('lessons/')) {
      tab.button.title = `${tab.path}\n${t('practice.readOnlyOriginal')}`;
    } else {
      tab.button.title = tab.path;
    }
  }

  private isDirty(tab: Tab): boolean {
    return tab.model !== null && tab.model.getAlternativeVersionId() !== tab.savedVersion;
  }

  private isWritable(tab: Tab): boolean {
    if (!this.originalWritable && tab.path.startsWith('lessons/')) return false;
    return tab.writable;
  }

  // --- files ---------------------------------------------------------------------------
  private async load(tab: Tab): Promise<void> {
    if (tab.model) return;
    const file = await api.readFile(tab.path);
    tab.model = monaco.editor.createModel(file.content, languageOf(tab.path),
      monaco.Uri.from({ scheme: 'repo', path: `/${tab.path}` }));
    tab.model.setEOL(monaco.editor.EndOfLineSequence.LF);
    tab.sha = file.sha;
    tab.writable = file.writable;
    tab.savedVersion = tab.model.getAlternativeVersionId();
    this.applyMarkers(tab);
  }

  private replaceContent(tab: Tab, content: string, sha: string | null): void {
    if (!tab.model) return;
    const view = this.active === tab ? this.editor.saveViewState() : null;
    tab.model.setValue(content);
    tab.sha = sha;
    tab.savedVersion = tab.model.getAlternativeVersionId();
    tab.conflict = false;
    if (view) this.editor.restoreViewState(view);
    this.applyMarkers(tab);
    if (this.active === tab) this.renderInline();
    this.renderTab(tab);
  }

  private async save(tab: Tab): Promise<boolean> {
    if (!tab.model || !this.isWritable(tab)) return true;
    const content = tab.model.getValue();
    const version = tab.model.getAlternativeVersionId();
    let result = await api.saveFile(tab.path, content, tab.sha);
    if (!result.ok) {
      const deleted = result.content === null; // removed on disk: overwrite re-creates it
      const choice = await this.askConflict(tab.path, deleted);
      if (choice === 'cancel') return false;
      if (choice === 'reload' && !deleted) {
        this.replaceContent(tab, result.content ?? '', result.sha);
        return true;
      }
      result = await api.saveFile(tab.path, content, result.sha);
      if (!result.ok) {
        this.notify(t('editor.changedWhileSaving', { path: tab.path }));
        return false;
      }
    }
    tab.sha = result.sha;
    tab.savedVersion = version;
    tab.conflict = false;
    this.renderTab(tab);
    this.onSaved(tab.path);
    return true;
  }

  /** On window focus: reload unmodified tabs whose file changed on disk; flag modified ones. */
  private async refreshFromDisk(): Promise<void> {
    for (const tab of [...this.tabs.values()]) {
      if (!tab.model) continue;
      const sha = tab.sha;
      const version = tab.model.getAlternativeVersionId();
      let file;
      try {
        file = await api.readFile(tab.path);
      } catch {
        continue; // removed on disk: keep the tab; saving reports it
      }
      // a save or an edit while the request was out makes this answer stale
      if (this.tabs.get(tab.path) !== tab || tab.sha !== sha || tab.model.getAlternativeVersionId() !== version) continue;
      if (file.sha === tab.sha) continue;
      if (this.isDirty(tab)) {
        tab.conflict = true;
        this.renderTab(tab);
      } else {
        this.replaceContent(tab, file.content, file.sha);
      }
    }
  }

  private applyMarkers(tab: Tab): void {
    const model = tab.model;
    if (!model) return;
    const list = this.diagnostics.get(tab.path) ?? [];
    monaco.editor.setModelMarkers(model, 'gcc', toMarkers(list, (line) =>
      line >= 1 && line <= model.getLineCount() ? model.getLineLength(line) : 0));
  }

  /**
   * Span times after the lines of the active tab's file. Each line gets its own class whose ::after
   * carries the text (rules in one <style>): Monaco 0.57 did not render `after` injected text here.
   */
  private renderInline(): void {
    const model = this.active?.model;
    const rules: string[] = [];
    const decorations: monaco.editor.IModelDeltaDecoration[] = [];
    for (const [line, text] of (this.active && this.inline.get(this.active.path)) || []) {
      if (!model || line < 1 || line > model.getLineCount()) continue;
      const cls = `inline-timing inline-timing-${line}`;
      rules.push(`.inline-timing-${line}::after { content: "${text.replace(/["\\]/g, '\\$&')}"; }`);
      decorations.push({
        range: new monaco.Range(line, 1, line, model.getLineMaxColumn(line)),
        options: { afterContentClassName: cls, stickiness: monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges },
      });
    }
    this.inlineStyle.textContent = rules.join('\n');
    this.inlineTimes.set(decorations);
  }

  /** Inline texts shown in the active file (for checks and screenshots). */
  inlineTexts(): string[] {
    return [...((this.active && this.inline.get(this.active.path)) || new Map<number, string>()).values()];
  }
}
