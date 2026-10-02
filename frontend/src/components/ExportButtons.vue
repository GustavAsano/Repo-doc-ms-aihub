<template>
  <div class="export-panel">
    <div class="export-row">
      <button class="export-btn pdf" :class="{ loading: loadingPdf }" :disabled="!canExport" @click="doExport('pdf')">
        <v-icon size="16" class="mr-2">mdi-file-pdf-box</v-icon>
        {{ loadingPdf ? 'Building…' : 'Download PDF' }}
      </button>
      <button class="export-btn word" :class="{ loading: loadingDocx }" :disabled="!canExport" @click="doExport('docx')">
        <v-icon size="16" class="mr-2">mdi-file-word-box</v-icon>
        {{ loadingDocx ? 'Building…' : 'Download Word' }}
      </button>
    </div>
    <DocVariantSelector />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import DocVariantSelector from '@/components/DocVariantSelector.vue';
import { useToast } from 'vue-toastification';
import { useAppStore } from '@/stores/store';
import { exportDoc } from '@/services/backend';

const store = useAppStore();
const toast = useToast();
const loadingPdf = ref(false);
const loadingDocx = ref(false);

const canExport = computed(() => store.hasActiveDocs && !store.generating && !store.variantSwitching && !loadingPdf.value && !loadingDocx.value);

async function doExport(format: 'pdf' | 'docx') {
  if (!store.repoState?.repo_name) return;
  if (format === 'pdf') loadingPdf.value = true;
  else loadingDocx.value = true;

  try {
    const res = await exportDoc(store.repoState.repo_name, format, store.repoState.language, store.selectedDocVariant);
    // Trigger browser download from base64
    const mime = format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
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
    loadingPdf.value = false;
    loadingDocx.value = false;
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
.export-panel { display: flex; flex-direction: column; gap: 10px; }
.export-row { display: flex; gap: 8px; }
.export-btn {
  flex: 1; padding: 8px 12px; border-radius: 6px; border: 1px solid rgb(var(--v-theme-border-strong));
  background: transparent; color: rgb(var(--v-theme-muted)); font-size: 12px; cursor: pointer;
  font-family: 'JetBrains Mono', monospace; transition: all 0.15s;
  display: flex; align-items: center; justify-content: center;
}
.export-btn:hover:not(:disabled) { border-color: rgb(var(--v-theme-subtle)); color: rgb(var(--v-theme-text)); }
.export-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.export-btn.pdf:hover:not(:disabled) { border-color: rgb(var(--v-theme-error-strong)); color: rgb(var(--v-theme-error-light)); }
.export-btn.word:hover:not(:disabled) { border-color: rgb(var(--v-theme-info)); color: rgb(var(--v-theme-info-light)); }
.export-btn.loading { opacity: 0.7; cursor: wait; }
</style>
