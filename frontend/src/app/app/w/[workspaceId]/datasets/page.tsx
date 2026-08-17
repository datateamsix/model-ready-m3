import { Database } from "lucide-react";
import { RouteStub } from "@/components/prem3/route-stub";

export default function Page() {
  return (
    <RouteStub
      icon={Database}
      title="Datasets"
      description="First-class Dataset objects, upload, and unlimited evaluation history land in Mission 2 prompt M2-12."
    />
  );
}
