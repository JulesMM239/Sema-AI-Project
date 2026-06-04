'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getAuthToken } from '@/lib/api';

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    if (getAuthToken()) router.replace('/app');
    else router.replace('/login');
  }, [router]);
  return null;
}
