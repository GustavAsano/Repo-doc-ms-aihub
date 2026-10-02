<template>
  <v-app-bar :elevation="1" class="app-header pl-8 pr-4">
    <template #prepend>
      <div class="h-100 pr-4 pl-4">
        <a href="https://genms-playground.com/" target="_blank" class="gen-ms-logo"
          ><img src="/LogoGenMS.png" alt="GenMS — Management Solutions"
        /></a>
      </div>
      <v-divider class="mx-2" inset vertical></v-divider>
    </template>
    <v-app-bar-title class="text-primary text-center">
      <span class="header-title">Repository Documentation</span>
    </v-app-bar-title>

    <v-btn
      icon="mdi-white-balance-sunny"
      variant="text"
      :title="themeToggleLabel"
      :aria-label="themeToggleLabel"
      :aria-pressed="theme.global.current.value.dark"
      @click="toggleTheme"
    />
    <v-dialog v-model="infoDialog" max-width="70%">
      <template #activator="{ props: activatorProps }">
        <v-btn prepend-icon="mdi-information-outline" v-bind="activatorProps">Info</v-btn>
      </template>

      <template #default>
        <v-card title="GenMS - Repository Documentation">
          <v-card-text>
            Repository Documentation is an AI project developed by the GenMS team in
            <a href="https://www.managementsolutions.com" target="_blank">Management Solutions</a>.
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn @click="infoDialog = false">Close</v-btn>
          </v-card-actions>
        </v-card>
      </template>
    </v-dialog>
  </v-app-bar>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useTheme } from 'vuetify';
import { saveTheme } from '@/utils/themePreference';

const infoDialog = ref(false);
const theme = useTheme();
const themeToggleLabel = computed(() => theme.global.current.value.dark ? 'Switch to light theme' : 'Switch to dark theme');
function toggleTheme() {
  const nextTheme = theme.global.current.value.dark ? 'light' : 'dark';
  theme.global.name.value = nextTheme;
  saveTheme(nextTheme);
}
</script>

<style scoped>
.app-header {
  background-color: rgb(var(--v-theme-panel)) !important;
  color: rgb(var(--v-theme-text)) !important;
}

.header-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 2rem;
  font-weight: 700;
}

.gen-ms-logo {
  width: auto;
  height: 100%;
  display: flex;
  align-items: center;
}

.gen-ms-logo img {
  height: 60%;
}
</style>
