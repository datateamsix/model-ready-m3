import { Route } from "lucide-react";
import { RouteStub } from "@/components/prem3/route-stub";
import { routes } from "@/lib/routes";

export default async function Page({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  return (
    <RouteStub
      icon={Route}
      title="Acquisition plan"
      description="The plan detail and Meridian Integration surface lands in Mission 2 prompt M2-14."
      backHref={routes.workspacePlans(workspaceId)}
      backLabel="Back to planning"
    />
  );
}
