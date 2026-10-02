export type AppTheme = 'light' | 'dark';
const STORAGE_KEY = 'repo-doc-theme';

export function getStoredTheme(): AppTheme | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === 'light' || value === 'dark' ? value : null;
  } catch {
    return null;
  }
}

export function getInitialTheme(): AppTheme {
  return getStoredTheme() ?? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
}

export function saveTheme(theme: AppTheme): void {
  try { localStorage.setItem(STORAGE_KEY, theme); } catch { /* Preference still applies to this session. */ }
}
