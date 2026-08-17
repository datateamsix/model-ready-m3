import { FileText } from "lucide-react";
import { RouteStub } from "@/components/prem3/route-stub";

export default function Page() {
  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10">
      <RouteStub
        icon={FileText}
        title="Terms of service"
        description="The production-presentable terms of service land in Mission 2 prompt M2-15."
      />
    </div>
  );
}
