import { AdminGate } from '@/components/AdminGate';
import { AdminShell } from '@/components/admin/AdminShell';

export default function AdminPage() {
  return (
    <AdminGate>
      <AdminShell />
    </AdminGate>
  );
}
