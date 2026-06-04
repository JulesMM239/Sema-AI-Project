import { AuthGate } from '@/components/AuthGate';
import { TranslateShell } from '@/components/translate/TranslateShell';

export default function TranslatePage() {
  return (
    <AuthGate>
      <TranslateShell />
    </AuthGate>
  );
}
