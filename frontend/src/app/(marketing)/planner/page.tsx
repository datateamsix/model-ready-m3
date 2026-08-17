import { Compass } from "lucide-react";
import { RouteStub } from "@/components/prem3/route-stub";

export default function Page() {
  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10">
      <RouteStub
        icon={Compass}
        title="PreM3 Planner"
        description="The free, deterministic MMM planning brief tool lands in Mission 2 prompt M2-08."
      />
    </div>
  );
}
