import { FlaskConical } from "lucide-react";
import { RouteStub } from "@/components/prem3/route-stub";
import { routes } from "@/lib/routes";

export default async function Page({
  params,
}: {
  params: Promise<{ workspaceId: string; datasetId: string }>;
}) {
  const { workspaceId, datasetId } = await params;
  return (
    <RouteStub
      icon={FlaskConical}
      title="Evaluation"
      description="Mission 1's run workspace (findings, MODEL_READY gate, Meridian EDA, experience/reflection) moves into this nested Dataset route in Mission 2 prompt M2-12, once real authenticated Dataset/run data exists."
      backHref={routes.workspaceDataset(workspaceId, datasetId)}
      backLabel="Back to dataset"
    />
  );
}
