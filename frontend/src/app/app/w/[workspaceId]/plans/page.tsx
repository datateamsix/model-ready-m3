import { Route } from "lucide-react";
import { RouteStub } from "@/components/prem3/route-stub";
import { routes } from "@/lib/routes";

export default async function Page({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = await params;
  return (
    <RouteStub
      icon={Route}
      title="Planning"
      description="The authenticated acquisition-planning / getting-organized intake lands in Mission 2 prompt M2-10."
      backHref={routes.workspace(workspaceId)}
      backLabel="Back to project"
    />
  );
}
