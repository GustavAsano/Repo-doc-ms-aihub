import '@mdi/font/css/materialdesignicons.css';
import 'vuetify/styles';
import { createVuetify } from 'vuetify';
import { getInitialTheme } from '@/utils/themePreference';

export default createVuetify({
  theme: {
    defaultTheme: getInitialTheme(),
    themes: {
      light: {
        dark: false,
        colors: {
          primary: '#087f72', secondary: '#e8edf3', surface: '#ffffff', background: '#f4f7fb',
          'on-surface': '#172033', 'on-background': '#172033',
          'panel': '#f9fbfd', 'elevated': '#edf2f7', 'hover': '#e5edf5',
          'border': '#d9e1eb', 'border-strong': '#b8c5d3',
          'text': '#172033', 'text-secondary': '#344155', 'muted': '#4b596c',
          'subtle': '#59677b', 'disabled': '#65758a',
          'primary-bright': '#076b60', 'success': '#087a54', 'error': '#b42335',
          'error-strong': '#c52e42', 'error-light': '#b42335',
          'info': '#245db0', 'info-light': '#245db0', 'violet': '#5542b8', 'warning': '#996400',
        },
      },
      dark: {
        dark: true,
        colors: {
          primary: '#14b8a6', secondary: '#1e1e1e', surface: '#0d1117', background: '#080c12',
          'on-surface': '#e5e7eb', 'on-background': '#e5e7eb',
          'panel': '#0a0e17', 'elevated': '#111827', 'hover': '#0f1623',
          'border': '#1f2937', 'border-strong': '#374151',
          'text': '#e5e7eb', 'text-secondary': '#d1d5db', 'muted': '#9ca3af',
          'subtle': '#929dae', 'disabled': '#8793a5',
          'primary-bright': '#5eead4', 'success': '#10b981', 'error': '#f87171',
          'error-strong': '#ef4444', 'error-light': '#fca5a5',
          'info': '#3b82f6', 'info-light': '#93c5fd', 'violet': '#818cf8', 'warning': '#f59e0b',
        },
      },
      light: {
        dark: false,
        colors: {
          primary: '#0f766e',
          secondary: '#e2e8f0',
          surface: '#ffffff',
          background: '#f1f5f9',
          'on-surface': '#0f172a',
          'on-background': '#0f172a',
        },
      },
    },
  },
});
