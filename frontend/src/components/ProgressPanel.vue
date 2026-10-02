<template>
  <div class="progress-panel">
    <!-- Header -->
    <div class="prog-header">
      <div class="prog-title">
        <div class="pulse-dot" :class="{ active: store.generating }"></div>
        <span>{{ store.generating ? 'Generating documentation…' : (store.hasActiveDocs ? 'Done' : 'Ready') }}</span>
      </div>
      <div v-if="store.progressCost !== null" class="cost-badge">
        ${{ store.progressCost.toFixed(4) }}
      </div>
    </div>

    <!-- Progress bar -->
    <div class="prog-bar-wrap">
      <div
        class="prog-bar-fill"
        :style="{ width: barPct + '%', transition: 'width 0.4s ease' }"
        :class="{ done: !store.generating && store.hasActiveDocs }"
      ></div>
    </div>
    <div class="prog-counts">
      <span v-if="store.progressTotal > 0">
        {{ store.progressCurrent }} / {{ store.generating ? '~' : '' }}{{ store.progressTotal }} LLM calls
      </span>
      <span v-if="store.progressPhase" class="prog-phase">{{ store.progressPhase }}</span>
    </div>

    <!-- Generate button -->
    <div class="gen-btn-row">
      <button
        v-if="!store.generating"
        class="gen-btn"
        :disabled="!canGenerate || store.loading"
        @click="generate"
      >
        <v-icon size="14" class="mr-1">mdi-file-document-edit-outline</v-icon>
        Generate docs
      </button>
      <button
        v-else
        class="gen-btn cancel-btn"
        @click="cancel"
      >
        <v-icon size="14" class="mr-1">mdi-stop-circle-outline</v-icon>
        Cancel
      </button>
    </div>

    <!-- Event log -->
    <div v-if="store.progressEvents.length > 0" class="event-log" ref="logEl">
      <div
        v-for="(ev, i) in store.progressEvents"
        :key="i"
        class="ev-line"
        :class="ev.event"
      >
        <span class="ev-icon">{{ eventIcon(String(ev.event)) }}</span>
        <span class="ev-msg">{{ eventLabel(ev) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue';
import { useToast } from 'vue-toastification';
import { useAppStore } from '@/stores/store';
import { generateDocs, getDocsServer, getLibrary } from '@/services/backend';

const store = useAppStore();
const toast = useToast();
const logEl = ref<HTMLElement | null>(null);
let abortCtrl: AbortController | null = null;

const canGenerate = computed(() =>
  !!store.repoState?.repo_name && store.llmSaved,
);

const barPct = computed(() => {
  if (!store.generating && store.hasActiveDocs) return 100;
  if (store.progressTotal === 0) return 0;
  return Math.min(99, Math.round((store.progressCurrent / store.progressTotal) * 100));
});

function eventIcon(event: string) {
  const m: Record<string, string> = { plan: '⚡', call_start: '→', call_end: '✓', done: '✦', error: '✗' };
  return m[event] ?? '·';
}
function sectionLabel(ev: Record<string, unknown>): string {
  const phase = String(ev.phase ?? '');
  const section = ev.section != null ? String(ev.section).toUpperCase() : null;
  const sidx = ev.section_index != null ? ev.section_index : null;
  const stotal = ev.total_sections != null ? ev.total_sections : null;
  const isFunctional = ev.doc_variant === 'functional' || phase.startsWith('functional_');
  const typePrefix = isFunctional ? 'Functional · ' : '';
  if (section && sidx != null && stotal != null)
    return `${typePrefix}Writing ${section} (${sidx}/${stotal})`;
  if (section)
    return `${typePrefix}Writing ${section}`;
  if (phase === 'section_writing' || phase === 'functional_section_writing')
    return `${typePrefix}Writing section`;
  if (phase === 'final_cleanup' || phase === 'functional_final_cleanup')
    return `${typePrefix}Final cleanup`;
  if (phase === 'evidence_extraction' || phase === 'functional_chunk_extraction')
    return 'Extracting evidence';
  return phase;
}

function eventLabel(ev: Record<string, unknown>) {
  if (ev.event === 'plan') return `${ev.doc_variant === 'functional' ? 'Functional' : 'Technical'} plan: ~${ev.total_calls} total calls`;
  if (ev.event === 'phase_done') return `${ev.doc_variant === 'functional' ? 'Functional' : 'Technical'} generation complete`;
  if (ev.event === 'call_start') return `[${ev.current_call}/${ev.total_calls}] ${sectionLabel(ev)}`;
  if (ev.event === 'call_end') {
    const cost = ev.call_cost_usd != null ? ` · $${(ev.call_cost_usd as number).toFixed(4)}` : '';
    return `✓ ${sectionLabel(ev)} [${ev.current_call}/${ev.total_calls}]${cost}`;
  }
  if (ev.event === 'done') return 'Documentation complete';
  if (ev.event === 'error') return `Error: ${ev.message}`;
  return String(ev.message ?? ev.event ?? '');
}

async function scrollLog() {
  await nextTick();
  if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight;
}

watch(() => store.progressEvents.length, scrollLog);

async function generate() {
  if (!store.repoState?.repo_name) return;
  store.generating = true;
  store.resetProgress();
  store.docsUrl = '';
  store.mkdocsPort = null;
  store.repoState.docs_generated = false;
  store.repoState.functional_docs_generated = false;

  const showFunc = ['technical_and_functional', 'functional_only'].includes(store.generationMode);

  abortCtrl = generateDocs(
    {
      repo_name: store.repoState.repo_name,
      language: store.language,
      generation_mode: store.generationMode,
      provider: store.llm.provider,
      model: store.llm.model,
      use_system_key: store.llm.useSystemKey,
      api_key: store.llm.apiKey,
      documentation_sections: store.enabledTechSections,
      functional_sections: showFunc ? store.enabledFuncSections : undefined,
    },
    (ev) => store.pushProgressEvent(ev),
    async (result) => {
      store.generating = false;
      store.repoState = { ...store.repoState, ...result };
      toast.success('Documentation generated!');
      getLibrary('technical').then(entries => { store.library = entries; }).catch(() => {});
      getLibrary('functional').then(entries => { store.functionalLibrary = entries; }).catch(() => {});
      // MkDocs may still be starting — retry until it's ready (up to ~20s)
      const maxRetries = 13;
      for (let i = 0; i < maxRetries; i++) {
        try {
          const srv = await getDocsServer();
          store.mkdocsPort = srv.port;
          store.docsUrl = srv.preview_url + '?v=' + Date.now();
          break;
        } catch {
          if (i < maxRetries - 1) {
            await new Promise(r => setTimeout(r, 1500));
          } else {
            toast.warning('Documentation site could not start. Try refreshing the Docs tab.');
          }
        }
      }
    },
    (msg) => {
      store.generating = false;
      toast.error(msg);
    },
  );
}

function cancel() {
  abortCtrl?.abort();
  store.generating = false;
  toast.warning('Generation cancelled');
}
</script>

<style scoped>
.progress-panel { display: flex; flex-direction: column; gap: 12px; }
.prog-header { display: flex; align-items: center; justify-content: space-between; }
.prog-title { display: flex; align-items: center; gap: 8px; font-size: 12px; color: rgb(var(--v-theme-muted)); font-family: 'JetBrains Mono', monospace; }
.pulse-dot { width: 8px; height: 8px; border-radius: 50%; background: rgb(var(--v-theme-border-strong)); flex-shrink: 0; }
.pulse-dot.active { background: rgb(var(--v-theme-primary)); animation: pulse 1.2s infinite; }
@keyframes pulse { 0%,100% { opacity:1; transform:scale(1); } 50% { opacity:0.5; transform:scale(1.3); } }
.cost-badge { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: rgb(var(--v-theme-primary)); background: rgba(var(--v-theme-primary), 0.12); padding: 2px 8px; border-radius: 10px; }
.prog-bar-wrap { height: 4px; background: rgb(var(--v-theme-border)); border-radius: 2px; overflow: hidden; }
.prog-bar-fill { height: 100%; background: rgb(var(--v-theme-primary)); border-radius: 2px; }
.prog-bar-fill.done { background: rgb(var(--v-theme-success)); }
.prog-counts { display: flex; justify-content: space-between; font-size: 10px; color: rgb(var(--v-theme-disabled)); font-family: 'JetBrains Mono', monospace; }
.prog-phase { color: rgb(var(--v-theme-subtle)); font-style: italic; }
.gen-btn-row { display: flex; }
.gen-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 7px 18px; border-radius: 6px; border: 1px solid rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.12); color: rgb(var(--v-theme-primary));
  font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 600;
  cursor: pointer; transition: background 0.15s, border-color 0.15s;
  letter-spacing: 0.04em;
}
.gen-btn:hover:not(:disabled) { background: rgba(var(--v-theme-primary), 0.22); }
.gen-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.cancel-btn { border-color: rgb(var(--v-theme-error)); background: rgba(var(--v-theme-error), 0.1); color: rgb(var(--v-theme-error)); }
.cancel-btn:hover { background: rgba(var(--v-theme-error), 0.2); }
.progress-panel { flex: 1; }
.event-log {
  flex: 1; min-height: 120px; max-height: 480px; overflow-y: auto; background: rgb(var(--v-theme-surface));
  border: 1px solid rgb(var(--v-theme-border)); border-radius: 6px; padding: 8px;
  display: flex; flex-direction: column; gap: 3px;
}
.ev-line { display: flex; gap: 8px; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: rgb(var(--v-theme-subtle)); }
.ev-icon { flex-shrink: 0; width: 14px; text-align: center; }
.ev-line.plan .ev-msg { color: rgb(var(--v-theme-violet)); }
.ev-line.call_start .ev-msg { color: rgb(var(--v-theme-muted)); }
.ev-line.call_end .ev-msg { color: rgb(var(--v-theme-disabled)); }
.ev-line.done .ev-msg { color: rgb(var(--v-theme-success)); font-weight: 600; }
.ev-line.error .ev-msg { color: rgb(var(--v-theme-error)); }
</style>
