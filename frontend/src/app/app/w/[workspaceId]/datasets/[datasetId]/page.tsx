import { Database } from "lucide-react";
import { RouteStub } from "@/components/prem3/route-stub";
import { routes } from "@/lib/routes";

export default async function Page({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  return (
    <RouteStub
      icon={Database}
      title="Dataset"
      description="Dataset detail (source inventory, upload state, evaluation history, artifacts) lands in Mission 2 prompt M2-12."
      backHref={routes.workspaceDatasets(workspaceId)}
      backLabel="Back to datasets"
    />
  );
}
