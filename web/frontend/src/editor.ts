// Editor area: Monaco with one tab per file (spec 070-02 §2.3).
// Files are the repository's own files: saving writes them (lessons/ only), and the sha of the
// version the tab started from detects edits made elsewhere (VS Code) as a conflict.

import 'monaco-editor/editor/editor.main';
import * as monaco from 'monaco-editor/editor/editor.api';
import EditorWorker from 'monaco-editor/editor/editor.worker?worker';
import { api, type Diagnostic } from './api';
import { groupByFile, toMarkers } from './diagnostics';

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
  if (/\.(c|cc|cpp|cxx|h|hh|hpp|hxx|ipp|inl)$/i.test(path)) return 'cpp';
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
  private readonly highlight: monaco.editor.IEditorDecorationsCollection;
  /** Called after a file is saved, so other views (README) can refresh. */
  onSaved: (path: string) => void = () => {};

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

  /** Open a file (adding a tab if needed) and optionally highlight one line. */
  async open(path: string, line?: number): Promise<void> {
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
    this.editor.setModel(tab.model);
    if (tab.view) this.editor.restoreViewState(tab.view);
    this.editor.updateOptions({ readOnly: !tab.writable });
    for (const t of this.tabs.values()) this.renderTab(t);
    this.highlight.clear();
    if (line !== undefined && tab.model) {
      const safe = Math.min(Math.max(1, line), tab.model.getLineCount());
      this.editor.revealLineInCenter(safe);
      this.editor.setPosition({ lineNumber: safe, column: 1 });
      this.highlight.set([{ range: new monaco.Range(safe, 1, safe, 1), options: { isWholeLine: true, className: 'line-highlight' } }]);
    }
    this.editor.focus();
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
    }
  }

  private renderTab(tab: Tab): void {
    const dirty = this.isDirty(tab);
    tab.button.textContent = `${tab.model && !tab.writable ? '🔒 ' : ''}${baseName(tab.path)}${dirty ? ' ●' : ''}`;
    tab.button.classList.toggle('active', tab === this.active);
    tab.button.classList.toggle('dirty', dirty);
    tab.button.classList.toggle('conflict', tab.conflict);
    tab.button.setAttribute('aria-selected', String(tab === this.active));
    tab.button.title = tab.conflict ? `${tab.path} — 디스크에서 바뀜 (저장하면 충돌 처리)` : tab.path;
  }

  private isDirty(tab: Tab): boolean {
    return tab.model !== null && tab.model.getAlternativeVersionId() !== tab.savedVersion;
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
    this.renderTab(tab);
  }

  private async save(tab: Tab): Promise<boolean> {
    if (!tab.model || !tab.writable) return true;
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
        this.notify(`${tab.path}: 저장하는 사이에 다시 바뀌었습니다. 다시 시도하세요.`);
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
}
