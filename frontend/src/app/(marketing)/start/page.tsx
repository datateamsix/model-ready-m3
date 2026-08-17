import { Flag } from "lucide-react";
import { RouteStub } from "@/components/prem3/route-stub";

export default function Page() {
  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10">
      <RouteStub
        icon={Flag}
        title="Get started"
        description="The customer-stage chooser (Planning / Getting organized / Ready to assess) lands in Mission 2 prompt M2-09."
      />
    </div>
  );
}
