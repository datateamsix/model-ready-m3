import { Compass } from "lucide-react";
import { RouteStub } from "@/components/prem3/route-stub";

export default function Page() {
  return (
    <RouteStub
      icon={Compass}
      title="PreM3 Planner"
      description="The free, deterministic MMM planning brief tool lands in Mission 2 prompt M2-08."
    />
  );
}
