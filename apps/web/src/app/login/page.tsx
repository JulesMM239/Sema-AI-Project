'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, setAuthToken } from '@/lib/api';
import { Button, Card, Input } from '@/components/ui';
import type React from 'react';

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res =
        mode === 'login'
          ? await api.login(email, password)
          : await api.signup(email, password, fullName);
      setAuthToken(res.access_token, res.is_admin);
      router.replace('/app');
    } catch (err: any) {
      setError(err?.message || 'Failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="text-2xl font-semibold tracking-tight text-night">SEMA.AI</div>
          <div className="mt-1 text-sm text-gray-600">
            Chat + Translation (Kivu ↔ Katanga)
          </div>
        </div>

        <Card className="p-6">
          <form onSubmit={onSubmit} className="space-y-4">
            {mode === 'signup' ? (
              <Input
                label="Full name (optional)"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Your name"
              />
            ) : null}

            <Input
              label="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              type="email"
              required
            />

            <Input
              label="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              required
            />

            {error ? (
              <div className="rounded-xl bg-red-50 border border-red-100 px-3 py-2 text-sm text-red-700">
                {error}
              </div>
            ) : null}

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
            </Button>

            <div className="text-center text-sm text-gray-600">
              {mode === 'login' ? (
                <button
                  type="button"
                  onClick={() => setMode('signup')}
                  className="text-night hover:underline"
                >
                  Need an account? Sign up
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setMode('login')}
                  className="text-night hover:underline"
                >
                  Already have an account? Sign in
                </button>
              )}
            </div>
          </form>
        </Card>

        <div className="mt-4 text-center text-xs text-gray-500">
          First registered user becomes Admin (MVP convenience).
        </div>
      </div>
    </div>
  );
}
