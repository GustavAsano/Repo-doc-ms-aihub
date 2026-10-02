<template>
  <v-app>
    <v-layout class="rounded rounded-md">
      <Header />
      <Main />
    </v-layout>
  </v-app>
</template>

<script setup lang="ts">
import { watch, onBeforeUnmount } from 'vue';
import { useTheme } from 'vuetify';
import { getStoredTheme } from '@/utils/themePreference';

const theme = useTheme();
const browserTheme = window.matchMedia('(prefers-color-scheme: dark)');
const updateSystemTheme = (event: MediaQueryListEvent) => {
  if (!getStoredTheme()) theme.global.name.value = event.matches ? 'dark' : 'light';
};
browserTheme.addEventListener('change', updateSystemTheme);
onBeforeUnmount(() => browserTheme.removeEventListener('change', updateSystemTheme));

watch(() => theme.global.name.value, (name) => {
  document.documentElement.classList.remove('v-theme--light', 'v-theme--dark');
  document.documentElement.classList.add(`v-theme--${name}`);
  document.documentElement.style.colorScheme = name;
}, { immediate: true });
</script>

<style>
body {
  font-family: 'Montserrat', sans-serif;
  background: rgb(var(--v-theme-background));
  color: rgb(var(--v-theme-text));
}
html {
  overflow-y: auto;
}
a { color: rgb(var(--v-theme-primary)); }
.Vue-Toastification__toast {
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-text));
  border: 1px solid rgb(var(--v-theme-border-strong));
}
.Vue-Toastification__toast--success { border-left: 4px solid rgb(var(--v-theme-success)); }
.Vue-Toastification__toast--error { border-left: 4px solid rgb(var(--v-theme-error)); }
.Vue-Toastification__toast--warning { border-left: 4px solid rgb(var(--v-theme-warning)); }
.Vue-Toastification__close-button { color: inherit; }
</style>
