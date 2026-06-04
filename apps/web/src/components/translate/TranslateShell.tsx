'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { MEDIA_BASE_URL } from '@/lib/env';
import { Button, Card, Select, Textarea } from '@/components/ui';
import { ArrowLeft, Mic, Send, Volume2 } from 'lucide-react';

export function TranslateShell() {
  const router = useRouter();
  const [source, setSource] = useState<'KIV' | 'KAT'>('KIV');
  const [target, setTarget] = useState<'KIV' | 'KAT'>('KAT');
  const [text, setText] = useState('');
  const [out, setOut] = useState('');
  const [audioPath, setAudioPath] = useState<string | null>(null);
  const [models, setModels] = useState<Array<{ id: string; exists: boolean; is_default: boolean }>>([]);
  const [modelId, setModelId] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

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
        const mm = await api.metaModels();
        const m = (mm.models || []) as any[];
        const slim = m.map((x) => ({ id: x.id as string, exists: !!x.exists, is_default: !!x.is_default }));
        setModels(slim);
        setModelId(slim.find((x) => x.is_default)?.id || slim[0]?.id || '');
      } catch (e: any) {
        setErr(e?.message || 'Failed to load models');
      }
    })();
  }, []);

  async function doTranslate() {
    const t = text.trim();
    if (!t) return;
    setBusy(true);
    setErr(null);
    try {
      const res = await api.translateText({ source_dialect: source, target_dialect: target, text: t, model_id: modelId || defaultModel });
      setOut(res.translated_text);
      setAudioPath(res.audio_path);
    } catch (e: any) {
      setErr(e?.message || 'Translate failed');
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

  async function stopRecordingAndTranslate() {
    const rec = recorderRef.current;
    if (!rec) return;
    setRecording(false);
    setBusy(true);
    rec.stop();
    await new Promise((r) => setTimeout(r, 120));

    const blob = new Blob(chunksRef.current, { type: 'audio/wav' });
    const form = new FormData();
    form.append('source_dialect', source);
    form.append('target_dialect', target);
    form.append('model_id', modelId || defaultModel);
    form.append('file', blob, 'voice.wav');

    try {
      const res = await api.translateAudio(form);
      setOut(res.translated_text);
      setAudioPath(res.audio_path);
    } catch (e: any) {
      setErr(e?.message || 'Audio translate failed');
    } finally {
      setBusy(false);
    }
  }

  const audioUrl = audioPath ? `${MEDIA_BASE_URL}/${audioPath}` : null;

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-5xl mx-auto p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button className="p-2 rounded-xl hover:bg-black/5" onClick={() => router.push('/app')}>
              <ArrowLeft size={18} />
            </button>
            <div>
              <div className="text-lg font-semibold text-night">Translation</div>
              <div className="text-xs text-gray-500">Kivu ↔ Katanga • Glossary-first, optional LLM polish</div>
            </div>
          </div>
          <div className="w-[280px]">
            <Select label="Model" value={modelId} onChange={(e) => setModelId(e.target.value)}>
              {models.length === 0 ? <option value="">(server not configured)</option> : null}
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id}{m.exists ? '' : ' (missing)'}{m.is_default ? ' ★' : ''}
                </option>
              ))}
            </Select>
          </div>
        </div>

        {err ? (
          <div className="mt-4 rounded-xl bg-red-50 border border-red-100 px-3 py-2 text-sm text-red-700">{err}</div>
        ) : null}

        <div className="mt-6 grid md:grid-cols-2 gap-6">
          <Card className="p-5">
            <div className="grid grid-cols-2 gap-3">
              <Select label="Source" value={source} onChange={(e) => setSource(e.target.value as any)}>
                <option value="KIV">Kivu</option>
                <option value="KAT">Katanga</option>
              </Select>
              <Select label="Target" value={target} onChange={(e) => setTarget(e.target.value as any)}>
                <option value="KAT">Katanga</option>
                <option value="KIV">Kivu</option>
              </Select>
            </div>
            <div className="mt-4">
              <Textarea value={text} onChange={(e) => setText(e.target.value)} label="Text" rows={8} placeholder="Andika hapa…" />
            </div>
            <div className="mt-4 flex items-center justify-between">
              <div className="text-xs text-gray-500">You can also translate by voice.</div>
              <div className="flex items-center gap-2">
                {recording ? (
                  <Button variant="danger" size="sm" onClick={stopRecordingAndTranslate} disabled={busy}>
                    <Mic size={16} className="mr-2" /> Stop
                  </Button>
                ) : (
                  <Button variant="ghost" size="sm" onClick={startRecording} disabled={busy}>
                    <Mic size={16} className="mr-2" /> Voice
                  </Button>
                )}
                <Button size="sm" onClick={doTranslate} disabled={busy}>
                  <Send size={16} className="mr-2" /> Translate
                </Button>
              </div>
            </div>
          </Card>

          <Card className="p-5">
            <div className="text-sm font-medium text-gray-900">Result</div>
            <div className="mt-3 whitespace-pre-wrap text-sm leading-relaxed">{out || <span className="text-gray-500">No result yet.</span>}</div>
            {audioUrl ? (
              <div className="mt-4 flex items-center gap-2">
                <Volume2 size={18} className="text-gray-500" />
                <audio controls src={audioUrl} className="w-full" />
              </div>
            ) : null}
          </Card>
        </div>
      </div>
    </div>
  );
}
