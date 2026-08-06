import SetupTokenGate from "@/components/SetupTokenGate";
import SetupWizard from "@/components/SetupWizard";
import { isSetupAuthorized } from "@/lib/auth";
import { getConfigStatus } from "@/lib/config";

export const dynamic = "force-dynamic";

export default async function SetupPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const authorized = await isSetupAuthorized();
  if (!authorized) {
    const { error } = await searchParams;
    return <SetupTokenGate hasError={!!error} />;
  }

  const status = await getConfigStatus();
  return <SetupWizard initialStatus={status} />;
}
