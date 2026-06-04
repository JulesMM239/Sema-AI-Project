'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, clearAuthToken, isAdmin } from '@/lib/api';
import { MEDIA_BASE_URL } from '@/lib/env';
import { Button, Select, Textarea } from '@/components/ui';
import {
  LogOut,
  Plus,
  Settings2,
  Volume2,
  Mic,
  Send,
  Languages,
  Shield,
} from 'lucide-react';

type Msg = {
  id: number;
  role: 'user' | 'assistant';
  text: string;
  dialect: string;
  audio_path?: string;
};

type Conv = { id: number; title: string; updated_at: string };

function fmtDial(d: string) {
  if (d === 'KIV') return 'Kivu';
  if (d === 'KAT') return 'Katanga';
  return 'Auto';
}

function MessageBubble({ m }: { m: Msg }) {
  const isUser = m.role === 'user';
  const audioUrl = m.audio_path ? `${MEDIA_BASE_URL}/${m.audio_path}` : null;

  return (
    <div className={isUser ? 'flex justify-end' : 'flex justify-start'}>
      <div
        className={
          isUser
            ? 'max-w-[85%] rounded-2xl bg-night text-white px-4 py-3 text-sm leading-relaxed'
            : 'max-w-[85%] rounded-2xl bg-gray-50 border border-gray-100 px-4 py-3 text-sm leading-relaxed'
        }
      >
        <div className="whitespace-pre-wrap">{m.text}</div>
        <div className="mt-2 flex items-center gap-3">
          <div className="text-[11px] opacity-70">{fmtDial(m.dialect)}</div>
          {audioUrl ? (
            <audio controls src={audioUrl} className="h-8" />
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function ChatShell() {
  const router = useRouter();
  const [convs, setConvs] = useState<Conv[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [dialect, setDialect] = useState<'AUTO' | 'KIV' | 'KAT'>('AUTO');
  const [models, setModels] = useState<Array<{ id: string; exists: boolean; is_default: boolean }>>([]);
  const [modelId, setModelId] = useState<string>('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const listRef = useRef<HTMLDivElement | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const [recording, setRecording] = useState(false);

  const defaultModel = useMemo(() => {
    const d = models.find((m) => m.is_default) || models[0];
    return d?.id || '';
  }, [models]);

  useEffect(() => {
    (async () => {
      try {
        const [c, mm] = await Promise.all([api.listConversations(), api.metaModels()]);
        setConvs(c);
        const m = (mm.models || []) as any[];
        const slim = m.map((x) => ({ id: x.id as string, exists: !!x.exists, is_default: !!x.is_default }));
        setModels(slim);
        setModelId(slim.find((x) => x.is_default)?.id || slim[0]?.id || '');
        if (c.length === 0) {
          const nc = await api.newConversation();
          setActiveId(nc.conversation_id);
          setConvs([...(c || []), { id: nc.conversation_id, title: nc.title, updated_at: new Date().toISOString() }]);
        } else {
          setActiveId(c[0].id);
        }
      } catch (e: any) {
        setErr(e?.message || 'Failed to load');
      }
    })();
  }, []);

  useEffect(() => {
    if (!activeId) return;
    (async () => {
      try {
        const msgs = await api.getMessages(activeId);
        setMessages(msgs as any);
        setTimeout(() => {
          listRef.current?.scrollTo({ top: 1e9, behavior: 'instant' as any });
        }, 0);
      } catch (e: any) {
        setErr(e?.message || 'Failed to load messages');
      }
    })();
  }, [activeId]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: 1e9, behavior: 'smooth' });
  }, [messages.length]);

  async function newChat() {
    setErr(null);
    try {
      const nc = await api.newConversation();
      const row = { id: nc.conversation_id, title: nc.title, updated_at: new Date().toISOString() };
      setConvs((prev) => [row, ...prev]);
      setActiveId(nc.conversation_id);
      setMessages([]);
    } catch (e: any) {
      setErr(e?.message || 'Failed to create chat');
    }
  }

  async function sendText() {
    if (!activeId) return;
    const text = input.trim();
    if (!text) return;
    setInput('');
    setErr(null);
    setBusy(true);
    const optimistic: Msg = {
      id: Date.now(),
      role: 'user',
      text,
      dialect,
    };
    setMessages((prev) => [...prev, optimistic]);
    try {
      const res = await api.chatText({ conversation_id: activeId, text, dialect, model_id: modelId || defaultModel });
      const assistant: Msg = {
        id: Date.now() + 1,
        role: 'assistant',
        text: res.assistant_text,
        dialect: res.detected_dialect,
        audio_path: res.assistant_audio_path,
      };
      setMessages((prev) => [...prev, assistant]);
      // refresh list titles
      const c = await api.listConversations();
      setConvs(c);
    } catch (e: any) {
      setErr(e?.message || 'Send failed');
    } finally {
      setBusy(false);
    }
  }

  async function startRecording() {
    setErr(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) chunksRef.current.push(ev.data);
      };
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
      };
      recorderRef.current = rec;
      rec.start();
      setRecording(true);
    } catch (e: any) {
      setErr(e?.message || 'Microphone permission denied');
    }
  }

  async function stopRecordingAndSend() {
    if (!activeId) return;
    const rec = recorderRef.current;
    if (!rec) return;
    setRecording(false);
    setBusy(true);
    rec.stop();
    await new Promise((r) => setTimeout(r, 120));
    const blob = new Blob(chunksRef.current, { type: 'audio/wav' });
    const form = new FormData();
    form.append('conversation_id', String(activeId));
    form.append('dialect', dialect);
    form.append('model_id', modelId || defaultModel);
    form.append('file', blob, 'voice.wav');
    try {
      const res = await api.chatAudio(form);
      // user text isn't returned; reload messages from server for accuracy
      const msgs = await api.getMessages(activeId);
      setMessages(msgs as any);
      const c = await api.listConversations();
      setConvs(c);
    } catch (e: any) {
      setErr(e?.message || 'Audio send failed');
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    clearAuthToken();
    router.replace('/login');
  }

  return (
    <div className="h-screen w-screen overflow-hidden bg-white">
      <div className="h-full grid grid-cols-[320px_1fr]">
        {/* Sidebar */}
        <aside className="h-full border-r border-gray-200 flex flex-col">
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-semibold text-night">SEMA.AI</div>
                <div className="text-xs text-gray-500">Swahili Kivu ↔ Katanga</div>
              </div>
              <div className="flex items-center gap-1">
                {isAdmin() ? (
                  <button
                    className="p-2 rounded-xl hover:bg-black/5"
                    onClick={() => router.push('/admin')}
                    title="Admin"
                  >
                    <Shield size={18} />
                  </button>
                ) : null}
                <button
                  className="p-2 rounded-xl hover:bg-black/5"
                  onClick={() => router.push('/translate')}
                  title="Translation"
                >
                  <Languages size={18} />
                </button>
                <button
                  className="p-2 rounded-xl hover:bg-black/5"
                  onClick={logout}
                  title="Log out"
                >
                  <LogOut size={18} />
                </button>
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <Button onClick={newChat} variant="ghost" className="w-full">
                <Plus size={16} className="mr-2" /> New chat
              </Button>
            </div>
          </div>

          <div className="p-4 border-b border-gray-200 space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <Select label="Dialect" value={dialect} onChange={(e) => setDialect(e.target.value as any)}>
                <option value="AUTO">Auto</option>
                <option value="KIV">Kivu</option>
                <option value="KAT">Katanga</option>
              </Select>
              <Select label="Model" value={modelId} onChange={(e) => setModelId(e.target.value)}>
                {models.length === 0 ? <option value="">(server not configured)</option> : null}
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.id}{m.exists ? '' : ' (missing)'}{m.is_default ? ' ★' : ''}
                  </option>
                ))}
              </Select>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Settings2 size={14} />
              Voice-first chat + auto dialect detection.
            </div>
          </div>

          <div className="flex-1 overflow-auto">
            <div className="p-2">
              {convs.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setActiveId(c.id)}
                  className={
                    (activeId === c.id
                      ? 'bg-night text-white'
                      : 'hover:bg-black/5 text-gray-900') +
                    ' w-full text-left rounded-xl px-3 py-2 text-sm mb-1'
                  }
                >
                  <div className="truncate">{c.title}</div>
                </button>
              ))}
            </div>
          </div>
        </aside>

        {/* Main */}
        <main className="h-full flex flex-col">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-gray-900">Chat</div>
              <div className="text-xs text-gray-500">Dialect: {fmtDial(dialect)} • Model: {modelId || defaultModel || '—'}</div>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Volume2 size={16} /> Audio replies enabled
            </div>
          </div>

          {err ? (
            <div className="px-6 pt-4">
              <div className="rounded-xl bg-red-50 border border-red-100 px-3 py-2 text-sm text-red-700">
                {err}
              </div>
            </div>
          ) : null}

          <div ref={listRef} className="flex-1 overflow-auto px-6 py-6 space-y-4">
            {messages.map((m) => (
              <MessageBubble key={m.id} m={m} />
            ))}
            {busy ? (
              <div className="text-xs text-gray-500">Working…</div>
            ) : null}
          </div>

          <div className="p-4 border-t border-gray-200">
            <div className="rounded-2xl border border-gray-200 p-3 bg-white shadow-sm">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Write in Swahili…"
                rows={3}
                className="border-0 focus:ring-0 resize-none"
              />
              <div className="mt-2 flex items-center justify-between">
                <div className="text-xs text-gray-500">
                  Tip: pick KIV/KAT to force a dialect, or AUTO to mirror.
                </div>
                <div className="flex items-center gap-2">
                  {recording ? (
                    <Button variant="danger" size="sm" onClick={stopRecordingAndSend} disabled={busy}>
                      <Mic size={16} className="mr-2" /> Stop & send
                    </Button>
                  ) : (
                    <Button variant="ghost" size="sm" onClick={startRecording} disabled={busy}>
                      <Mic size={16} className="mr-2" /> Voice
                    </Button>
                  )}
                  <Button size="sm" onClick={sendText} disabled={busy}>
                    <Send size={16} className="mr-2" /> Send
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
