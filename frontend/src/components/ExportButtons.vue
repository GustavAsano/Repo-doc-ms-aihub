<template>
  <div class="export-panel">
    <!-- Technical docs row -->
    <div v-if="store.repoState?.docs_generated" class="variant-section">
      <span class="variant-title">Technical</span>
      <div class="export-row">
        <button class="export-btn pdf" :class="{ loading: loading.tech_pdf }" @click="doExport('pdf', 'technical')">
          <v-icon size="16" class="mr-2">mdi-file-pdf-box</v-icon>
          {{ loading.tech_pdf ? 'Building…' : 'PDF' }}
        </button>
        <button class="export-btn word" :class="{ loading: loading.tech_docx }" @click="doExport('docx', 'technical')">
          <v-icon size="16" class="mr-2">mdi-file-word-box</v-icon>
          {{ loading.tech_docx ? 'Building…' : 'Word' }}
        </button>
      </div>
    </div>

    <!-- Functional docs row -->
    <div v-if="store.repoState?.functional_docs_generated" class="variant-section">
      <span class="variant-title">Functional</span>
      <div class="export-row">
        <button class="export-btn pdf" :class="{ loading: loading.func_pdf }" @click="doExport('pdf', 'functional')">
          <v-icon size="16" class="mr-2">mdi-file-pdf-box</v-icon>
          {{ loading.func_pdf ? 'Building…' : 'PDF' }}
        </button>
        <button class="export-btn word" :class="{ loading: loading.func_docx }" @click="doExport('docx', 'functional')">
          <v-icon size="16" class="mr-2">mdi-file-word-box</v-icon>
          {{ loading.func_docx ? 'Building…' : 'Word' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue';
import { useToast } from 'vue-toastification';
import { useAppStore } from '@/stores/store';
import { exportDoc } from '@/services/backend';

const store = useAppStore();
const toast = useToast();

const loading = reactive({ tech_pdf: false, tech_docx: false, func_pdf: false, func_docx: false });

async function doExport(format: 'pdf' | 'docx', variant: 'technical' | 'functional') {
  if (!store.repoState?.repo_name) return;
  const key = `${variant === 'technical' ? 'tech' : 'func'}_${format}` as keyof typeof loading;
  loading[key] = true;

  try {
    const res = await exportDoc(store.repoState.repo_name, format, store.language, variant);
    const mime = format === 'pdf'
      ? 'application/pdf'
      : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    const blob = b64toBlob(res.data, mime);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = res.filename;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`${format.toUpperCase()} downloaded`);
  } catch (e: unknown) {
    toast.error('Export failed: ' + String(e));
  } finally {
    loading[key] = false;
  }
}

function b64toBlob(b64: string, type: string): Blob {
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return new Blob([arr], { type });
}
</script>

<style scoped>
.export-panel { display: flex; flex-direction: column; gap: 8px; }
.variant-section { display: flex; flex-direction: column; gap: 4px; }
.variant-title { font-size: 10px; color: #6b7280; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: 0.05em; }
.export-row { display: flex; gap: 8px; }
.export-btn {
  flex: 1; padding: 7px 10px; border-radius: 6px; border: 1px solid #374151;
  background: transparent; color: #9ca3af; font-size: 12px; cursor: pointer;
  font-family: 'JetBrains Mono', monospace; transition: all 0.15s;
  display: flex; align-items: center; justify-content: center;
}
.export-btn:hover:not(:disabled) { border-color: rgb(var(--v-theme-subtle)); color: rgb(var(--v-theme-text)); }
.export-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.export-btn.pdf:hover:not(:disabled) { border-color: rgb(var(--v-theme-error-strong)); color: rgb(var(--v-theme-error-light)); }
.export-btn.word:hover:not(:disabled) { border-color: rgb(var(--v-theme-info)); color: rgb(var(--v-theme-info-light)); }
.export-btn.loading { opacity: 0.7; cursor: wait; }
</style>
