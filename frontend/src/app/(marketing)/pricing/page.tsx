import { CreditCard } from "lucide-react";
import { RouteStub } from "@/components/prem3/route-stub";

export default function Page() {
  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10">
      <RouteStub
        icon={CreditCard}
        title="Pricing"
        description="Planner / Project / Portfolio / Enterprise packaging lands in Mission 2 prompt M2-05."
      />
    </div>
  );
}
