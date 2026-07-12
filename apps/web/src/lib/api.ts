// apps/web/src/lib/api.ts
import { API_BASE_URL } from './env';

export interface TokenResponse {
  access_token: string;
  token_type: string;
  is_admin: boolean;
}

export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('sema_token');
}

export function setAuthToken(token: string, admin: boolean) {
  if (typeof window === 'undefined') return;
  localStorage.setItem('sema_token', token);
  localStorage.setItem('sema_is_admin', admin ? '1' : '0');
}

export function clearAuthToken() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('sema_token');
  localStorage.removeItem('sema_is_admin');
}

export function isAdmin(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem('sema_is_admin') === '1';
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getAuthToken();

  const headers: Record<string, string> = {
    ...((opts.headers as Record<string, string>) || {}),
  };

  // Only set JSON content-type if body is not FormData and not already set.
  const isFormData =
    typeof FormData !== 'undefined' && opts.body instanceof FormData;

  if (!isFormData && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...opts,
    headers,
    cache: 'no-store',
  });

  if (!res.ok) {
    let detail = res.statusText || 'Request failed';
    try {
      const ct = res.headers.get('content-type') || '';
      if (ct.includes('application/json')) {
        const j = await res.json();
        detail = j?.detail || JSON.stringify(j);
      } else {
        detail = await res.text();
      }
    } catch {
      // ignore
    }
    throw new Error(`${res.status}: ${detail}`);
  }

  if (res.status === 204) return undefined as unknown as T;

  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return (await res.json()) as T;
  return (await res.text()) as unknown as T;
}

export const api = {
  signup: (email: string, password: string, fullName: string) =>
    request<TokenResponse>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name: fullName }),
    }),

  login: (email: string, password: string) =>
    request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  metaModels: () => request<{ models: any[] }>('/meta/models'),

  newConversation: () =>
    request<{ conversation_id: number; title: string }>('/conversations/new', {
      method: 'POST',
    }),

  listConversations: () =>
    request<Array<{ id: number; title: string; updated_at: string }>>(
      '/conversations/list'
    ),

  getMessages: (conversationId: number) =>
    request<any[]>(`/conversations/${conversationId}/messages`),

  chatText: (payload: {
    conversation_id: number;
    text: string;
    dialect: string;
    model_id?: string | null;
  }) =>
    request<{
      conversation_id: number;
      detected_dialect: string;
      assistant_text: string;
      assistant_audio_path: string;
    }>('/chat/text', { method: 'POST', body: JSON.stringify(payload) }),

  chatAudio: (form: FormData) =>
    request<{
      conversation_id: number;
      detected_dialect: string;
      assistant_text: string;
      assistant_audio_path: string;
    }>('/chat/audio', { method: 'POST', body: form }),

  translateText: (params: {
    source_dialect: string;
    target_dialect: string;
    text: string;
    model_id?: string | null;
  }) => {
    const form = new FormData();
    form.append('source_dialect', params.source_dialect);
    form.append('target_dialect', params.target_dialect);
    form.append('text', params.text);
    if (params.model_id) form.append('model_id', params.model_id);
    return request<{ translated_text: string; audio_path: string }>(
      '/translate/text',
      { method: 'POST', body: form }
    );
  },

  translateAudio: (form: FormData) =>
    request<{ translated_text: string; audio_path: string }>(
      '/translate/audio',
      { method: 'POST', body: form }
    ),

  adminRetrain: () =>
    request<{ job_id: number; status: string; model_version: string }>(
      '/admin/retrain',
      { method: 'POST' }
    ),

  adminJobs: () => request<any[]>('/admin/jobs'),

  adminAddCorpus: (dialect: string, text: string) =>
    request<{ ok: boolean; id: number }>(
      `/admin/add_corpus?dialect=${encodeURIComponent(
        dialect
      )}&text=${encodeURIComponent(text)}`,
      { method: 'POST' }
    ),

  adminUploadGlossary: (form: FormData) =>
    request<any>('/admin/upload_glossary', { method: 'POST', body: form }),

  adminUploadAudio: (form: FormData) =>
    request<any>('/admin/upload_audio', { method: 'POST', body: form }),

  // GGUF model registry
  adminListModels: () => request<any>('/admin/models'),

  adminUploadModel: (form: FormData) =>
    request<any>('/admin/models/upload', { method: 'POST', body: form }),

  adminRegisterModel: (model_id: string, path: string, label?: string) =>
    request<any>(
      `/admin/models/register?model_id=${encodeURIComponent(
        model_id
      )}&path=${encodeURIComponent(path)}${
        label ? `&label=${encodeURIComponent(label)}` : ''
      }`,
      { method: 'POST' }
    ),

  adminSetDefaultModel: (model_id: string) =>
    request<any>(
      `/admin/models/default?model_id=${encodeURIComponent(model_id)}`,
      { method: 'POST' }
    ),

  adminDeleteModel: (model_id: string, delete_file: boolean = false) =>
    request<any>(
      `/admin/models/${encodeURIComponent(
        model_id
      )}?delete_file=${delete_file ? 'true' : 'false'}`,
      { method: 'DELETE' }
    ),
};
