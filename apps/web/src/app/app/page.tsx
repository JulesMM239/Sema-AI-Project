import { AuthGate } from '@/components/AuthGate';
import { ChatShell } from '@/components/chat/ChatShell';

export default function AppPage() {
  return (
    <AuthGate>
      <ChatShell />
    </AuthGate>
  );
}
