import { Database } from "lucide-react";
import { RouteStub } from "@/components/prem3/route-stub";

export default function Page() {
  return (
    <RouteStub
      icon={Database}
      title="Dataset"
      description="Dataset detail (source inventory, upload state, evaluation history, artifacts) lands in Mission 2 prompt M2-12."
    />
  );
}
