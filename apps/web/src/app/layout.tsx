import './globals.css';
import type { Metadata } from 'next';
import type React from 'react';

export const metadata: Metadata = {
  title: 'SEMA.AI',
  description: 'Swahili (Kivu ↔ Katanga) chat & translation',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
