<template>
  <div v-if="store.availableDocVariants.length" class="variant-selector">
    <span class="variant-label">Documentation:</span>
    <button
      v-for="variant in store.availableDocVariants"
      :key="variant"
      class="variant-btn"
      :class="{ active: store.selectedDocVariant === variant }"
      :disabled="store.variantSwitching || store.generating"
      @click="select(variant)"
    >{{ variant === 'technical' ? 'Technical' : 'Functional' }}</button>
    <span v-if="store.variantSwitching" class="variant-label">Loading…</span>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios';
import { useToast } from 'vue-toastification';
import { useAppStore } from '@/stores/store';

const store = useAppStore();
const toast = useToast();

async function select(variant: 'technical' | 'functional') {
  if (variant === store.selectedDocVariant) return;
  try {
    await store.switchDocVariant(variant);
  } catch (e: unknown) {
    const detail = axios.isAxiosError(e)
      ? e.response?.data?.detail ?? e.response?.data?.error ?? e.message
      : String(e);
    toast.error('Could not switch documentation: ' + detail);
  }
}
</script>

<style scoped>
.variant-selector { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.variant-label { font-size: 10px; color: rgb(var(--v-theme-muted)); font-family: 'JetBrains Mono', monospace; }
.variant-btn {
  padding: 3px 10px; border-radius: 3px; border: 1px solid rgb(var(--v-theme-border-strong));
  background: transparent; color: rgb(var(--v-theme-muted)); font-size: 11px; cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
}
.variant-btn.active { border-color: rgb(var(--v-theme-primary)); color: rgb(var(--v-theme-primary)); }
.variant-btn:disabled { opacity: 0.5; cursor: wait; }
</style>
