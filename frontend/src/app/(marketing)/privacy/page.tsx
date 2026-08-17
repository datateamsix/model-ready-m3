import { Shield } from "lucide-react";
import { RouteStub } from "@/components/prem3/route-stub";

export default function Page() {
  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10">
      <RouteStub
        icon={Shield}
        title="Privacy policy"
        description="The production-presentable privacy policy lands in Mission 2 prompt M2-15."
      />
    </div>
  );
}
