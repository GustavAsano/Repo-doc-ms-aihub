<template>
  <div class="docs-viewer">
    <div class="docs-toolbar">
      <span class="docs-label">
        <v-icon size="14" class="mr-1" color="primary">mdi-book-open-page-variant-outline</v-icon>
        Documentation
      </span>
      <DocVariantSelector />
      <div class="docs-actions">
        <button v-if="store.docsUrl" class="tool-btn" title="Open in new tab" @click="openTab">
          <v-icon size="15">mdi-open-in-new</v-icon>
        </button>
        <button class="tool-btn" title="Refresh" @click="refresh">
          <v-icon size="15">mdi-refresh</v-icon>
        </button>
        <div v-if="store.mkdocsPort" class="port-badge">:{{ store.mkdocsPort }}</div>
      </div>
    </div>

    <div v-if="!store.docsUrl" class="docs-placeholder">
      <v-icon size="40" color="border-strong">mdi-file-document-outline</v-icon>
      <span class="ph-text">Generate documentation to preview it here</span>
    </div>

    <iframe
      v-else
      :key="store.docsUrl"
      ref="iframeEl"
      :src="iframeSrc"
      class="docs-iframe"
      frameborder="0"
      @load="onIframeLoad"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useTheme } from 'vuetify';
import DocVariantSelector from '@/components/DocVariantSelector.vue';
import { useAppStore } from '@/stores/store';

const store = useAppStore();
const theme = useTheme();
const iframeEl = ref<HTMLIFrameElement | null>(null);
const iframeLoaded = ref(false);
const bust = ref(0);

const iframeSrc = computed(() => {
  if (!store.docsUrl) return '';
  const base = store.docsUrl.startsWith('http') ? store.docsUrl : window.location.origin + store.docsUrl;
  const url = new URL(base);
  if (bust.value > 0) url.searchParams.set('_v', String(bust.value));
  return url.toString();
});

function syncDocumentationTheme() {
  const doc = iframeEl.value?.contentDocument;
  if (!doc?.body) return;
  doc.body.setAttribute('data-md-color-scheme', theme.global.current.value.dark ? 'slate' : 'default');
  doc.documentElement.style.colorScheme = theme.global.current.value.dark ? 'dark' : 'light';
}
function onIframeLoad() {
  iframeLoaded.value = true;
  syncDocumentationTheme();
}
watch(() => theme.global.name.value, syncDocumentationTheme);

function openTab() { window.open(store.docsUrl, '_blank'); }
function refresh() { bust.value++; iframeLoaded.value = false; }

watch(() => store.docsUrl, (newVal, oldVal) => {
  iframeLoaded.value = false;
  if (newVal && !oldVal) bust.value++;
});
</script>

<style scoped>
.docs-viewer { display: flex; flex-direction: column; height: 100%; }
.docs-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; background: rgb(var(--v-theme-surface)); border-bottom: 1px solid rgb(var(--v-theme-border)); flex-shrink: 0;
}
.docs-label { display: flex; align-items: center; font-size: 12px; color: rgb(var(--v-theme-muted)); font-family: 'JetBrains Mono', monospace; }
.docs-actions { display: flex; align-items: center; gap: 6px; }
.tool-btn {
  width: 28px; height: 28px; border-radius: 4px; border: 1px solid rgb(var(--v-theme-border-strong));
  background: transparent; color: rgb(var(--v-theme-subtle)); cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: all 0.15s;
}
.tool-btn:hover { border-color: rgb(var(--v-theme-subtle)); color: rgb(var(--v-theme-text-secondary)); }
.port-badge { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: rgb(var(--v-theme-disabled)); }
.docs-placeholder { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; background: rgb(var(--v-theme-surface)); }
.ph-text { font-size: 12px; color: rgb(var(--v-theme-disabled)); font-family: 'JetBrains Mono', monospace; text-align: center; max-width: 260px; }
.docs-iframe { flex: 1; width: 100%; border: none; background: rgb(var(--v-theme-surface)); }
</style>

<style>
.v-theme--light .docs-toolbar { background: #ffffff; border-bottom-color: #e2e8f0; }
.v-theme--light .docs-label { color: #475569; }
.v-theme--light .tool-btn { border-color: #e2e8f0; color: #94a3b8; }
.v-theme--light .tool-btn:hover { border-color: #94a3b8; color: #0f172a; }
.v-theme--light .port-badge { color: #94a3b8; }
.v-theme--light .docs-placeholder { background: #f8fafc; }
.v-theme--light .ph-text { color: #94a3b8; }
</style>
