'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Button, Card, Input, Select, Textarea } from '@/components/ui';
import { ArrowLeft, RefreshCw, Upload, PlusCircle, ListChecks } from 'lucide-react';
import { Trash2, Star, PackagePlus } from 'lucide-react';

export function AdminShell() {
  const router = useRouter();
  const [jobs, setJobs] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [corpusDialect, setCorpusDialect] = useState<'KIV' | 'KAT'>('KIV');
  const [corpusText, setCorpusText] = useState('');

  const [audioDialect, setAudioDialect] = useState<'KIV' | 'KAT'>('KIV');
  const [audioText, setAudioText] = useState('');
  const [audioSpeaker, setAudioSpeaker] = useState('default');
  const [audioFile, setAudioFile] = useState<File | null>(null);

  const [glossaryFile, setGlossaryFile] = useState<File | null>(null);

  // Model registry
  const [modelFile, setModelFile] = useState<File | null>(null);
  const [modelsInfo, setModelsInfo] = useState<any | null>(null);

  async function refresh() {
    setErr(null);
    try {
      const j = await api.adminJobs();
      setJobs(j);
      // Load models in parallel (non-blocking)
      try {
        const mi = await api.adminListModels();
        setModelsInfo(mi);
      } catch {
        // ignore
      }
    } catch (e: any) {
      setErr(e?.message || 'Failed to load jobs');
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function retrain() {
    setBusy(true);
    setErr(null);
    try {
      await api.adminRetrain();
      await refresh();
    } catch (e: any) {
      setErr(e?.message || 'Retrain failed');
    } finally {
      setBusy(false);
    }
  }

  async function uploadGlossary() {
    if (!glossaryFile) return;
    setBusy(true);
    setErr(null);
    try {
      const fd = new FormData();
      fd.append('file', glossaryFile);
      await api.adminUploadGlossary(fd);
    } catch (e: any) {
      setErr(e?.message || 'Upload failed');
    } finally {
      setBusy(false);
    }
  }

  async function addCorpus() {
    const t = corpusText.trim();
    if (!t) return;
    setBusy(true);
    setErr(null);
    try {
      await api.adminAddCorpus(corpusDialect, t);
      setCorpusText('');
    } catch (e: any) {
      setErr(e?.message || 'Add corpus failed');
    } finally {
      setBusy(false);
    }
  }

  async function uploadAudio() {
    if (!audioFile) return;
    const t = audioText.trim();
    if (!t) return;
    setBusy(true);
    setErr(null);
    try {
      const fd = new FormData();
      fd.append('dialect', audioDialect);
      fd.append('text', t);
      fd.append('speaker', audioSpeaker);
      fd.append('file', audioFile);
      await api.adminUploadAudio(fd);
      setAudioText('');
      setAudioFile(null);
    } catch (e: any) {
      setErr(e?.message || 'Upload audio failed');
    } finally {
      setBusy(false);
    }
  }

  async function uploadModel() {
    if (!modelFile) return;
    setBusy(true);
    setErr(null);
    try {
      const fd = new FormData();
      fd.append('file', modelFile);
      await api.adminUploadModel(fd);
      setModelFile(null);
      await refresh();
    } catch (e: any) {
      setErr(e?.message || 'Upload model failed');
    } finally {
      setBusy(false);
    }
  }

  async function registerScanned(path: string) {
    setBusy(true);
    setErr(null);
    try {
      const id = (path.split('/').pop() || '').trim();
      await api.adminRegisterModel(id, path, id.replace(/\.gguf$/i, ''));
      await refresh();
    } catch (e: any) {
      setErr(e?.message || 'Register failed');
    } finally {
      setBusy(false);
    }
  }

  async function setDefaultModel(id: string) {
    setBusy(true);
    setErr(null);
    try {
      await api.adminSetDefaultModel(id);
      await refresh();
    } catch (e: any) {
      setErr(e?.message || 'Set default failed');
    } finally {
      setBusy(false);
    }
  }

  async function deleteModel(id: string, deleteFile: boolean) {
    setBusy(true);
    setErr(null);
    try {
      await api.adminDeleteModel(id, deleteFile);
      await refresh();
    } catch (e: any) {
      setErr(e?.message || 'Delete failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-6xl mx-auto p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button className="p-2 rounded-xl hover:bg-black/5" onClick={() => router.push('/app')}>
              <ArrowLeft size={18} />
            </button>
            <div>
              <div className="text-lg font-semibold text-night">Admin</div>
              <div className="text-xs text-gray-500">Training queue, glossary & dataset inputs</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={refresh} disabled={busy}>
              <RefreshCw size={16} className="mr-2" /> Refresh
            </Button>
            <Button onClick={retrain} disabled={busy}>
              <ListChecks size={16} className="mr-2" /> Retrain pipeline
            </Button>
          </div>
        </div>

        {err ? (
          <div className="mt-4 rounded-xl bg-red-50 border border-red-100 px-3 py-2 text-sm text-red-700">{err}</div>
        ) : null}

        <div className="mt-6 grid lg:grid-cols-3 gap-6">
          <Card className="p-5 lg:col-span-2">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-900">Training jobs</div>
                <div className="text-xs text-gray-500">Latest 20 jobs</div>
              </div>
            </div>
            <div className="mt-4 overflow-auto">
              <table className="w-full text-sm">
                <thead className="text-xs text-gray-500">
                  <tr>
                    <th className="text-left py-2">ID</th>
                    <th className="text-left py-2">Version</th>
                    <th className="text-left py-2">Status</th>
                    <th className="text-left py-2">Notes</th>
                    <th className="text-left py-2">Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((j) => (
                    <tr key={j.id} className="border-t border-gray-100">
                      <td className="py-2 pr-2">{j.id}</td>
                      <td className="py-2 pr-2">{j.model_version}</td>
                      <td className="py-2 pr-2">{j.status}</td>
                      <td className="py-2 pr-2 max-w-[360px] truncate" title={j.notes || ''}>{j.notes}</td>
                      <td className="py-2 pr-2 text-xs text-gray-500">{(j.updated_at || '').slice(0, 19).replace('T', ' ')}</td>
                    </tr>
                  ))}
                  {jobs.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-gray-500">No jobs yet.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
            <div className="mt-4 text-xs text-gray-500">
              Note: this MVP builds datasets/manifests and translation packs. Heavy fine-tuning can be added later.
            </div>
          </Card>

          <Card className="p-5">
            <div className="text-sm font-medium text-gray-900">Upload glossary (CSV)</div>
            <div className="mt-3 space-y-3">
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setGlossaryFile(e.target.files?.[0] || null)}
                className="block w-full text-sm"
              />
              <Button variant="ghost" onClick={uploadGlossary} disabled={busy || !glossaryFile}>
                <Upload size={16} className="mr-2" /> Upload
              </Button>
              <div className="text-xs text-gray-500">
                Updating the glossary immediately impacts dialect mapping and future translation pack builds.
              </div>
            </div>
          </Card>

          <Card className="p-5">
            <div className="text-sm font-medium text-gray-900">Add corpus text</div>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <Select label="Dialect" value={corpusDialect} onChange={(e) => setCorpusDialect(e.target.value as any)}>
                <option value="KIV">Kivu</option>
                <option value="KAT">Katanga</option>
              </Select>
              <div />
            </div>
            <div className="mt-3">
              <Textarea label="Text" value={corpusText} onChange={(e) => setCorpusText(e.target.value)} rows={5} placeholder="Sentence or paragraph…" />
            </div>
            <div className="mt-3 flex justify-end">
              <Button size="sm" onClick={addCorpus} disabled={busy}>
                <PlusCircle size={16} className="mr-2" /> Add
              </Button>
            </div>
          </Card>

          <Card className="p-5 lg:col-span-2">
            <div className="text-sm font-medium text-gray-900">Upload labeled audio (WAV)</div>
            <div className="mt-3 grid md:grid-cols-3 gap-3">
              <Select label="Dialect" value={audioDialect} onChange={(e) => setAudioDialect(e.target.value as any)}>
                <option value="KIV">Kivu</option>
                <option value="KAT">Katanga</option>
              </Select>
              <Input label="Speaker" value={audioSpeaker} onChange={(e) => setAudioSpeaker(e.target.value)} placeholder="default" />
              <label className="block">
                <div className="mb-1 text-xs text-gray-600">WAV file</div>
                <input
                  type="file"
                  accept=".wav"
                  onChange={(e) => setAudioFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm"
                />
              </label>
            </div>
            <div className="mt-3">
              <Textarea label="Transcript" value={audioText} onChange={(e) => setAudioText(e.target.value)} rows={3} placeholder="Exact words spoken in the WAV…" />
            </div>
            <div className="mt-3 flex justify-end">
              <Button size="sm" onClick={uploadAudio} disabled={busy || !audioFile}>
                <Upload size={16} className="mr-2" /> Upload
              </Button>
            </div>
            <div className="mt-3 text-xs text-gray-500">
              Audio labels are stored server-side to prepare ASR/TTS training datasets.
            </div>
          </Card>

          <Card className="p-5 lg:col-span-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-gray-900">LLM Models (GGUF)</div>
                <div className="text-xs text-gray-500">Upload, register and set a default model for the dropdown</div>
              </div>
              <div className="text-xs text-gray-500">Registry: {modelsInfo?.registry_path || '/models/registry.json'}</div>
            </div>

            <div className="mt-4 grid md:grid-cols-3 gap-4">
              <div className="md:col-span-1">
                <div className="text-xs text-gray-600 mb-2">Upload a .gguf file</div>
                <input type="file" accept=".gguf" onChange={(e) => setModelFile(e.target.files?.[0] || null)} className="block w-full text-sm" />
                <div className="mt-2">
                  <Button variant="ghost" onClick={uploadModel} disabled={busy || !modelFile}>
                    <Upload size={16} className="mr-2" /> Upload & Register
                  </Button>
                </div>
                <div className="mt-2 text-xs text-gray-500">
                  Tip: large GGUF files can take time. Make sure your docker volume has enough space.
                </div>
              </div>

              <div className="md:col-span-2">
                <div className="text-xs text-gray-600 mb-2">Registered models</div>
                <div className="overflow-auto rounded-xl border border-gray-100">
                  <table className="w-full text-sm">
                    <thead className="text-xs text-gray-500">
                      <tr>
                        <th className="text-left py-2 px-3">Model</th>
                        <th className="text-left py-2 px-3">Path</th>
                        <th className="text-left py-2 px-3">Status</th>
                        <th className="text-right py-2 px-3">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(modelsInfo?.registered || []).map((m: any) => (
                        <tr key={m.id} className="border-t border-gray-100">
                          <td className="py-2 px-3">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{m.id}</span>
                              {m.is_default ? <span className="text-xs bg-yellow-100 text-yellow-900 px-2 py-0.5 rounded-full">default</span> : null}
                            </div>
                          </td>
                          <td className="py-2 px-3 text-xs text-gray-600 max-w-[420px] truncate" title={m.path}>{m.path}</td>
                          <td className="py-2 px-3 text-xs">{m.exists ? <span className="text-green-700">exists</span> : <span className="text-red-700">missing</span>}</td>
                          <td className="py-2 px-3">
                            <div className="flex justify-end gap-2">
                              <Button size="sm" variant="ghost" onClick={() => setDefaultModel(m.id)} disabled={busy}>
                                <Star size={16} className="mr-2" /> Default
                              </Button>
                              <Button size="sm" variant="ghost" onClick={() => deleteModel(m.id, false)} disabled={busy}>
                                <Trash2 size={16} className="mr-2" /> Remove
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                      {(modelsInfo?.registered || []).length === 0 ? (
                        <tr>
                          <td colSpan={4} className="py-6 text-center text-gray-500">No registered models yet.</td>
                        </tr>
                      ) : null}
                    </tbody>
                  </table>
                </div>

                <div className="mt-4">
                  <div className="text-xs text-gray-600 mb-2">Scanned GGUF files (not registered)</div>
                  <div className="grid md:grid-cols-2 gap-2">
                    {(modelsInfo?.scanned || [])
                      .filter((s: any) => !(modelsInfo?.registered || []).some((r: any) => r.id === s.id))
                      .slice(0, 10)
                      .map((s: any) => (
                        <div key={s.path} className="flex items-center justify-between rounded-xl border border-gray-100 px-3 py-2">
                          <div className="min-w-0">
                            <div className="text-sm font-medium truncate">{s.id}</div>
                            <div className="text-xs text-gray-500 truncate" title={s.path}>{s.path}</div>
                          </div>
                          <Button size="sm" variant="ghost" onClick={() => registerScanned(s.path)} disabled={busy}>
                            <PackagePlus size={16} className="mr-2" /> Register
                          </Button>
                        </div>
                      ))}
                    {((modelsInfo?.scanned || []).length === 0) ? (
                      <div className="text-xs text-gray-500">No GGUF files found in /models or /models/gguf.</div>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
