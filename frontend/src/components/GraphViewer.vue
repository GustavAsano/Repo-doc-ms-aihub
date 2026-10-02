<template>
  <div class="graph-viewer">
    <div class="graph-toolbar">
      <span class="graph-title">
        <v-icon size="14" class="mr-1" color="primary">mdi-graph-outline</v-icon>
        Dependency Graph
        <span v-if="totalNodes > 0" class="node-count">{{ totalNodes }} nodes · {{ totalEdges }} edges</span>
      </span>
      <button class="tool-btn" title="Reload" @click="loadGraph">
        <v-icon size="16">mdi-refresh</v-icon>
      </button>
    </div>

    <div v-if="loading" class="graph-placeholder">
      <v-progress-circular indeterminate color="primary" size="28" />
    </div>
    <div v-else-if="!groups.length" class="graph-placeholder">
      <v-icon size="36" color="border-strong">mdi-graph-outline</v-icon>
      <span class="ph-text">No graph available yet</span>
    </div>

    <div v-else class="groups-scroll">
      <!-- General: all nodes -->
      <div class="group-section">
        <div class="group-header" @click="toggleGroup('__all__')">
          <v-icon size="13" class="chevron" :class="{ rotated: !expanded['__all__'] }">mdi-chevron-down</v-icon>
          <span class="group-name">General</span>
          <span class="group-meta">{{ totalNodes }} nodes · {{ totalEdges }} edges</span>
        </div>
        <div v-show="expanded['__all__']"
             :ref="(el: Element | ComponentPublicInstance | null) => setGroupEl('__all__', el)"
             class="cy-group-container"
             :style="{ height: groupHeight(totalNodes) + 'px' }">
        </div>
      </div>

      <!-- Per-folder groups -->
      <div v-for="group in groups" :key="group.name" class="group-section">
        <div class="group-header" @click="toggleGroup(group.name)">
          <v-icon size="13" class="chevron" :class="{ rotated: !expanded[group.name] }">mdi-chevron-down</v-icon>
          <span class="group-name">> {{ group.name }}</span>
          <span class="group-meta">{{ group.nodes.length }} nodes · {{ group.edges.length }} edges</span>
        </div>
        <div v-show="expanded[group.name]"
             :ref="(el: Element | ComponentPublicInstance | null) => setGroupEl(group.name, el)"
             class="cy-group-container"
             :style="{ height: groupHeight(group.nodes.length) + 'px' }">
        </div>
      </div>
    </div>

    <div v-if="selectedNode" class="node-detail">
      <div class="nd-path">{{ selectedNode.path }}</div>
      <div class="nd-type">{{ selectedNode.tipo }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ComponentPublicInstance = any;
import { useAppStore } from '@/stores/store';
import { useTheme } from 'vuetify';
import { getGraph } from '@/services/backend';

const store = useAppStore();
const theme = useTheme();
const loading = ref(false);
const totalNodes = ref(0);
const totalEdges = ref(0);
const selectedNode = ref<Record<string, unknown> | null>(null);

interface GraphGroup {
  name: string;
  nodes: Record<string, unknown>[];
  edges: Record<string, unknown>[];
}

const groups = ref<GraphGroup[]>([]);
const expanded = reactive<Record<string, boolean>>({});
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const cyInstances = new Map<string, any>();
const groupEls = new Map<string, HTMLElement>();

// All nodes/edges stored for the General group
let allNodes: Record<string, unknown>[] = [];
let allEdges: Record<string, unknown>[] = [];

function groupHeight(nodeCount: number): number {
  if (nodeCount <= 8)  return 280;
  if (nodeCount <= 20) return 400;
  if (nodeCount <= 50) return 540;
  if (nodeCount <= 100) return 680;
  return 820;
}

function shortLabel(n: Record<string, unknown>): string {
  // Prefer explicit name field over full path
  const name = String(n.name ?? n.nome ?? '').trim();
  if (name && name !== String(n.path ?? '')) return name;
  // Fall back to last segment of path
  const path = String(n.path ?? n.label ?? n.id ?? '').replace(/\\/g, '/');
  const segments = path.split('/').filter(Boolean);
  return segments[segments.length - 1] || path;
}

function setGroupEl(key: string, el: Element | ComponentPublicInstance | null) {
  if (el instanceof HTMLElement) {
    groupEls.set(key, el);
  } else if (el === null) {
    groupEls.delete(key);
  }
}

function buildElements(nodes: Record<string, unknown>[], edges: Record<string, unknown>[]) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodeEls: any[] = nodes.map((n) => ({
    group: 'nodes',
    data: {
      id: String(n.id ?? n.path ?? ''),
      label: shortLabel(n),
      path: String(n.path ?? ''),
      tipo: String(n.tipo ?? n.kind ?? ''),
    },
  }));
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const edgeEls: any[] = edges.map((e, i) => ({
    group: 'edges',
    data: {
      id: `e${i}`,
      source: String(e.source ?? e.from ?? ''),
      target: String(e.target ?? e.to ?? ''),
    },
  }));
  return [...nodeEls, ...edgeEls];
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function cyStyle() {
  const dark = theme.global.current.value.dark;
  return [
    {
      selector: 'node',
      style: {
        'background-color': (dark ? '#1e3a4a' : '#d8e8f0'),
        'border-color': (dark ? '#2d6a7a' : '#52788e'),
        'border-width': 1,
        'label': 'data(label)',
        'color': (dark ? '#e2e8f0' : '#24364b'),
        'font-size': '9px',
        'font-family': 'JetBrains Mono, monospace',
        'text-valign': 'bottom',
        'text-halign': 'center',
        'text-margin-y': 4,
        'text-outline-color': (dark ? '#080c12' : '#f4f7fb'),
        'text-outline-width': 2,
        'text-wrap': 'ellipsis',
        'text-max-width': '90px',
        'width': 26,
        'height': 26,
      },
    },
    {
      selector: 'node[tipo="module"]',
      style: {
        'background-color': (dark ? '#0d4f4a' : '#cef1e9'),
        'border-color': (dark ? '#14b8a6' : '#087f72'),
        'border-width': 2,
        'width': 28,
        'height': 28,
        'color': (dark ? '#5eead4' : '#076b60'),
      },
    },
    {
      selector: 'node[tipo="class"]',
      style: {
        'background-color': (dark ? '#312e6e' : '#e4ddfa'),
        'border-color': (dark ? '#6366f1' : '#5542b8'),
        'color': (dark ? '#a5b4fc' : '#49359a'),
      },
    },
    {
      selector: 'node[tipo="function"]',
      style: {
        'background-color': (dark ? '#1c2f20' : '#d8eedf'),
        'border-color': (dark ? '#4ade80' : '#208146'),
        'color': (dark ? '#86efac' : '#206039'),
      },
    },
    {
      selector: 'node:selected',
      style: { 'border-color': (dark ? '#f59e0b' : '#996400'), 'border-width': 2 },
    },
    {
      selector: 'edge',
      style: {
        'line-color': (dark ? '#4b6480' : '#687b91'),
        'target-arrow-color': (dark ? '#6b8da6' : '#536b87'),
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'width': 1.5,
        'opacity': 0.75,
      },
    },
  ];
}

async function renderGroup(key: string, nodes: Record<string, unknown>[], edges: Record<string, unknown>[]) {
  const container = groupEls.get(key);
  if (!container) return;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const cytoscape = ((await import('cytoscape')) as any).default ?? (await import('cytoscape'));

  const existing = cyInstances.get(key);
  if (existing) existing.destroy();

  const cy = cytoscape({
    container,
    elements: buildElements(nodes, edges),
    style: cyStyle(),
    layout: {
      name: 'cose',
      animate: false,
      nodeRepulsion: () => 80000,
      idealEdgeLength: () => 140,
      nodeOverlap: 24,
      gravity: 0.15,
      numIter: 1000,
      padding: 40,
      randomize: true,
      componentSpacing: 80,
    },
    wheelSensitivity: 0.2,
  });

  cy.on('tap', 'node', (evt: { target: { data: () => Record<string, unknown> } }) => {
    selectedNode.value = evt.target.data();
  });
  cy.on('tap', (evt: { target: unknown }) => {
    if (evt.target === cy) selectedNode.value = null;
  });

  cyInstances.set(key, cy);
}

async function toggleGroup(key: string) {
  expanded[key] = !expanded[key];
  if (!expanded[key]) return;
  await nextTick();
  if (cyInstances.has(key)) {
    cyInstances.get(key)?.resize();
    cyInstances.get(key)?.fit(undefined, 24);
    return;
  }
  if (key === '__all__') {
    await renderGroup('__all__', allNodes, allEdges);
  } else {
    const group = groups.value.find((g) => g.name === key);
    if (group) await renderGroup(key, group.nodes, group.edges);
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function buildGroups(data: any): GraphGroup[] {
  const nodes: Record<string, unknown>[] = data.nodes ?? [];
  const edges: Record<string, unknown>[] = data.edges ?? [];

  const groupMap: Record<string, Record<string, unknown>[]> = {};
  for (const n of nodes) {
    const path = String(n.path ?? '').replace(/\\/g, '/');
    const topDir = path.includes('/') ? path.split('/')[0] : 'root';
    if (!groupMap[topDir]) groupMap[topDir] = [];
    groupMap[topDir].push(n);
  }

  return Object.entries(groupMap)
    .map(([name, gnodes]) => {
      const idSet = new Set(gnodes.map((n) => n.id));
      const gedges = edges.filter((e) => idSet.has(e.from ?? e.source) && idSet.has(e.to ?? e.target));
      return { name, nodes: gnodes, edges: gedges };
    })
    .sort((a: GraphGroup, b: GraphGroup) => a.name.localeCompare(b.name));
}

async function loadGraph() {
  if (!store.repoState?.repo_name) return;
  loading.value = true;
  // destroy old instances
  cyInstances.forEach((c) => c.destroy());
  cyInstances.clear();
  groups.value = [];
  Object.keys(expanded).forEach((k) => delete expanded[k]);

  try {
    const data = await getGraph(store.repoState.repo_name, store.language);
    store.graphData = data;
    if (!data) return;

    allNodes = data.nodes ?? [];
    allEdges = data.edges ?? [];
    totalNodes.value = allNodes.length;
    totalEdges.value = allEdges.length;

    groups.value = buildGroups(data);

    // Start with General expanded, all folders collapsed
    expanded['__all__'] = true;
    groups.value.forEach((g) => { expanded[(g as GraphGroup).name] = false; });

    loading.value = false;
    await nextTick();
    await renderGroup('__all__', allNodes, allEdges);
  } catch (err) {
    console.warn('[GraphViewer] loadGraph failed:', err);
  } finally {
    loading.value = false;
  }
}

watch(() => store.repoState?.repo_name, (name: string | undefined, prev: string | undefined) => {
  if (!name) { groups.value = []; store.graphData = null; return; }
  if (name !== prev) { groups.value = []; store.graphData = null; }
  loadGraph();
});

watch(() => theme.global.name.value, () => {
  cyInstances.forEach(cy => cy.style(cyStyle()).update());
});

onMounted(() => { if (store.repoState?.repo_name) loadGraph(); });
onBeforeUnmount(() => { cyInstances.forEach((c) => c.destroy()); cyInstances.clear(); });
</script>

<style scoped>
.graph-viewer { display: flex; flex-direction: column; height: 100%; overflow: hidden; }

.graph-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; background: rgb(var(--v-theme-surface)); border-bottom: 1px solid rgb(var(--v-theme-border)); flex-shrink: 0;
}
.graph-title { display: flex; align-items: center; gap: 6px; font-size: 12px; color: rgb(var(--v-theme-muted)); font-family: 'JetBrains Mono', monospace; }
.node-count { font-size: 10px; color: rgb(var(--v-theme-disabled)); margin-left: 8px; }
.tool-btn {
  width: 28px; height: 28px; border-radius: 4px; border: 1px solid rgb(var(--v-theme-border-strong));
  background: transparent; color: rgb(var(--v-theme-subtle)); cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.tool-btn:hover { border-color: rgb(var(--v-theme-subtle)); color: rgb(var(--v-theme-text-secondary)); }

.graph-placeholder { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; background: rgb(var(--v-theme-surface)); }
.ph-text { font-size: 12px; color: rgb(var(--v-theme-disabled)); font-family: 'JetBrains Mono', monospace; }

.groups-scroll { flex: 1; overflow-y: auto; background: rgb(var(--v-theme-background)); }
.groups-scroll::-webkit-scrollbar { width: 4px; }
.groups-scroll::-webkit-scrollbar-thumb { background: rgb(var(--v-theme-border)); border-radius: 2px; }

.group-section { border-bottom: 1px solid rgb(var(--v-theme-elevated)); }
.group-header {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 14px; cursor: pointer; user-select: none;
  background: rgb(var(--v-theme-panel));
  font-family: 'JetBrains Mono', monospace; font-size: 12px; color: rgb(var(--v-theme-muted));
  transition: background 0.12s, color 0.12s;
}
.group-header:hover { background: rgb(var(--v-theme-hover)); color: rgb(var(--v-theme-text)); }
.chevron { transition: transform 0.18s; color: rgb(var(--v-theme-disabled)); }
.chevron.rotated { transform: rotate(-90deg); }
.group-name { flex: 1; color: rgb(var(--v-theme-text-secondary)); }
.group-meta { font-size: 10px; color: rgb(var(--v-theme-disabled)); }

.cy-group-container { width: 100%; background: rgb(var(--v-theme-background)); }

.node-detail {
  padding: 8px 12px; background: rgb(var(--v-theme-elevated)); border-top: 1px solid rgb(var(--v-theme-border));
  font-family: 'JetBrains Mono', monospace; flex-shrink: 0;
}
.nd-path { font-size: 11px; color: rgb(var(--v-theme-primary)); }
.nd-type { font-size: 10px; color: rgb(var(--v-theme-subtle)); margin-top: 2px; }
</style>
