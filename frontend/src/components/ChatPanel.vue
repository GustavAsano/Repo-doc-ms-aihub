<template>
  <div class="chat-panel">
    <!-- Session sidebar -->
    <div class="sessions-sidebar">
      <div class="sessions-header">
        <span class="sessions-title">Chats</span>
        <button class="icon-btn" title="New chat" @click="newSession">
          <v-icon size="14">mdi-plus</v-icon>
        </button>
      </div>
      <div class="sessions-list">
        <div
          v-for="s in store.chatSessions"
          :key="s.session_id"
          class="session-item"
          :class="{ active: s.session_id === store.activeChatSessionId }"
          @click="switchSession(s.session_id)"
        >
          <span class="session-title">{{ s.title }}</span>
          <button class="del-btn" title="Delete" @click.stop="deleteSession(s.session_id)">
            <v-icon size="11">mdi-close</v-icon>
          </button>
        </div>
        <div v-if="store.chatSessions.length === 0" class="sessions-empty">No chats yet</div>
      </div>
    </div>

    <!-- Chat area -->
    <div class="chat-area">
      <div class="chat-header">
        <v-icon size="14" color="primary" class="mr-1">mdi-message-text-outline</v-icon>
        <span>{{ activeSessionTitle }}</span>
      </div>

      <div class="messages" ref="messagesEl">
        <div v-if="store.chatHistory.length === 0" class="chat-empty">
          <v-icon size="28" color="border-strong">mdi-robot-outline</v-icon>
          <span>Ask anything about {{ store.repoName || 'the repository' }}</span>
        </div>
        <template v-else>
          <div
            v-for="(msg, i) in store.chatHistory"
            :key="i"
            class="message"
            :class="msg.role"
          >
            <div class="msg-role">{{ msg.role === 'user' ? 'You' : 'AI' }}</div>
            <div class="msg-content" v-html="renderMd(msg.content)"></div>
          </div>
        </template>
        <div v-if="store.chatLoading" class="message assistant">
          <div class="msg-role">AI</div>
          <div class="typing-dots"><span></span><span></span><span></span></div>
        </div>
      </div>

      <div class="chat-input-row">
        <v-text-field
          v-model="question"
          placeholder="Ask about the code…"
          density="compact"
          variant="outlined"
          hide-details
          class="dark-input flex-1"
          :disabled="!canChat || store.chatLoading"
          @keydown.enter.exact.prevent="send"
        />
        <button
          class="send-btn"
          :disabled="!canChat || !question.trim() || store.chatLoading"
          @click="send"
        >
          <v-icon size="16">mdi-send</v-icon>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue';
import { useToast } from 'vue-toastification';
import { useAppStore } from '@/stores/store';
import { sendChatMessage, getChatHistory, deleteChatSession, listChatSessions } from '@/services/backend';

const store = useAppStore();
const toast = useToast();
const question = ref('');
const messagesEl = ref<HTMLElement | null>(null);

const canChat = computed(() => !!store.repoState?.repo_name && store.llmSaved);

const activeSessionTitle = computed(() => {
  const s = store.chatSessions.find(s => s.session_id === store.activeChatSessionId);
  return s?.title ?? 'Ask about the codebase';
});

function renderMd(text: string): string {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/```[\w]*\n?([\s\S]*?)```/g, '<pre class="code-block">$1</pre>')
    .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
}

async function scrollBottom() {
  await nextTick();
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
}

watch(() => store.chatHistory.length, scrollBottom);

async function loadSessions(repoName: string) {
  try {
    store.chatSessions = await listChatSessions(repoName);
  } catch {
    store.chatSessions = [];
  }
}

async function loadHistory(sessionId: string) {
  const repo = store.repoState?.repo_name;
  if (!repo) return;
  try {
    store.chatHistory = await getChatHistory(repo, sessionId === '__default__' ? undefined : sessionId);
  } catch {
    store.chatHistory = [];
  }
  scrollBottom();
}

watch(() => store.repoState?.repo_name, async (name) => {
  store.chatHistory = [];
  store.chatSessions = [];
  store.activeChatSessionId = '';
  if (!name) return;
  await loadSessions(name);
  if (store.chatSessions.length > 0) {
    store.activeChatSessionId = store.chatSessions[0].session_id;
    await loadHistory(store.activeChatSessionId);
  }
});

function newSession() {
  const id = crypto.randomUUID();
  store.activeChatSessionId = id;
  store.chatHistory = [];
  // Don't persist empty session — it will be saved on first message
}

async function switchSession(sessionId: string) {
  if (sessionId === store.activeChatSessionId) return;
  store.activeChatSessionId = sessionId;
  await loadHistory(sessionId);
}

async function deleteSession(sessionId: string) {
  const repo = store.repoState?.repo_name;
  if (!repo) return;
  try {
    await deleteChatSession(repo, sessionId === '__default__' ? undefined : sessionId);
    store.chatSessions = store.chatSessions.filter(s => s.session_id !== sessionId);
    if (store.activeChatSessionId === sessionId) {
      if (store.chatSessions.length > 0) {
        store.activeChatSessionId = store.chatSessions[0].session_id;
        await loadHistory(store.activeChatSessionId);
      } else {
        store.activeChatSessionId = '';
        store.chatHistory = [];
      }
    }
  } catch {
    toast.error('Failed to delete chat');
  }
}

async function send() {
  const q = question.value.trim();
  if (!q || !store.repoState?.repo_name) return;

  // Create a new session ID if none active
  if (!store.activeChatSessionId) {
    store.activeChatSessionId = crypto.randomUUID();
  }

  question.value = '';
  store.chatLoading = true;
  store.chatHistory.push({ role: 'user', content: q });
  scrollBottom();

  const sessionId = store.activeChatSessionId;
  try {
    const res = await sendChatMessage(
      store.repoState.repo_name,
      q,
      store.language,
      store.llm,
      sessionId === '__default__' ? undefined : sessionId,
    );
    store.chatHistory = res.history;
    // Refresh session list to pick up new title / new session entry
    await loadSessions(store.repoState.repo_name);
    // If this was a brand new session not yet in the list, ensure it's selected
    if (!store.chatSessions.find(s => s.session_id === sessionId)) {
      await loadSessions(store.repoState.repo_name);
    }
  } catch (e: unknown) {
    toast.error('Chat failed: ' + String(e));
    store.chatHistory.push({ role: 'assistant', content: 'Error: ' + String(e) });
  } finally {
    store.chatLoading = false;
    scrollBottom();
  }
}
</script>

<style scoped>
.chat-panel { display: flex; height: 100%; overflow: hidden; }

/* Session sidebar */
.sessions-sidebar {
  width: 180px; flex-shrink: 0;
  background: rgb(var(--v-theme-surface)); border-right: 1px solid rgb(var(--v-theme-border));
  display: flex; flex-direction: column; overflow: hidden;
}
.sessions-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 10px; border-bottom: 1px solid rgb(var(--v-theme-border)); flex-shrink: 0;
}
.sessions-title { font-size: 10px; color: rgb(var(--v-theme-disabled)); font-family: 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: 0.08em; }
.icon-btn {
  background: transparent; border: 1px solid rgb(var(--v-theme-border-strong)); color: rgb(var(--v-theme-subtle));
  border-radius: 4px; width: 20px; height: 20px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.15s;
}
.icon-btn:hover { border-color: rgb(var(--v-theme-primary)); color: rgb(var(--v-theme-primary)); }
.sessions-list { flex: 1; overflow-y: auto; padding: 6px; display: flex; flex-direction: column; gap: 2px; }
.session-item {
  display: flex; align-items: center; gap: 4px;
  padding: 6px 8px; border-radius: 5px; cursor: pointer;
  border: 1px solid transparent; transition: all 0.15s;
}
.session-item:hover { background: rgb(var(--v-theme-border)); border-color: rgb(var(--v-theme-border-strong)); }
.session-item.active { background: rgba(var(--v-theme-primary), 0.08); border-color: rgba(var(--v-theme-primary), 0.3); }
.session-title {
  flex: 1; font-size: 11px; color: rgb(var(--v-theme-muted)); font-family: 'JetBrains Mono', monospace;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.session-item.active .session-title { color: rgb(var(--v-theme-primary)); }
.del-btn {
  flex-shrink: 0; background: transparent; border: none; color: rgb(var(--v-theme-border-strong));
  cursor: pointer; display: flex; align-items: center; padding: 1px;
  border-radius: 3px; transition: color 0.15s; opacity: 0;
}
.session-item:hover .del-btn { opacity: 1; }
.del-btn:hover { color: rgb(var(--v-theme-error)); }
.sessions-empty { font-size: 10px; color: rgb(var(--v-theme-border-strong)); font-family: 'JetBrains Mono', monospace; padding: 10px 8px; }

/* Chat area */
.chat-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.chat-header {
  display: flex; align-items: center; gap: 6px; padding: 8px 12px;
  background: rgb(var(--v-theme-surface)); border-bottom: 1px solid rgb(var(--v-theme-border)); flex-shrink: 0;
  font-size: 12px; color: rgb(var(--v-theme-muted)); font-family: 'JetBrains Mono', monospace;
}
.messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 14px; background: rgb(var(--v-theme-background)); }
.chat-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; color: rgb(var(--v-theme-disabled)); font-size: 12px; font-family: 'JetBrains Mono', monospace; }
.message { display: flex; flex-direction: column; gap: 4px; max-width: 85%; }
.message.user { align-self: flex-end; }
.message.assistant { align-self: flex-start; }
.msg-role { font-size: 10px; font-family: 'JetBrains Mono', monospace; color: rgb(var(--v-theme-disabled)); }
.message.user .msg-role { text-align: right; color: rgb(var(--v-theme-primary)); }
.msg-content {
  font-size: 13px; color: rgb(var(--v-theme-text-secondary)); line-height: 1.6;
  background: rgb(var(--v-theme-elevated)); border-radius: 8px; padding: 10px 14px;
  border: 1px solid rgb(var(--v-theme-border));
}
.message.user .msg-content { background: rgba(var(--v-theme-primary), 0.1); border-color: rgba(var(--v-theme-primary), 0.2); color: rgb(var(--v-theme-text)); }
:deep(.code-block) { background: rgb(var(--v-theme-surface)); border: 1px solid rgb(var(--v-theme-border-strong)); border-radius: 4px; padding: 10px; font-family: 'JetBrains Mono', monospace; font-size: 11px; overflow-x: auto; color: rgb(var(--v-theme-muted)); white-space: pre; }
:deep(.inline-code) { background: rgb(var(--v-theme-border)); border-radius: 3px; padding: 1px 5px; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: rgb(var(--v-theme-primary)); }
.typing-dots { display: flex; gap: 4px; padding: 8px 12px; background: rgb(var(--v-theme-elevated)); border-radius: 8px; border: 1px solid rgb(var(--v-theme-border)); }
.typing-dots span { width: 6px; height: 6px; border-radius: 50%; background: rgb(var(--v-theme-disabled)); animation: bounce 1.2s infinite; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,100% { transform:translateY(0); } 50% { transform:translateY(-4px); } }
.chat-input-row { display: flex; gap: 8px; padding: 10px 12px; background: rgb(var(--v-theme-surface)); border-top: 1px solid rgb(var(--v-theme-border)); flex-shrink: 0; }
.send-btn {
  width: 36px; height: 36px; border-radius: 6px; border: 1px solid rgb(var(--v-theme-border-strong));
  background: transparent; color: rgb(var(--v-theme-subtle)); cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: all 0.15s; flex-shrink: 0;
}
.send-btn:hover:not(:disabled) { border-color: rgb(var(--v-theme-primary)); color: rgb(var(--v-theme-primary)); }
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
