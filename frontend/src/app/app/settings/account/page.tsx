import { User } from "lucide-react";
import { RouteStub } from "@/components/prem3/route-stub";

export default function Page() {
  return (
    <RouteStub
      icon={User}
      title="Account settings"
      description="Clerk-supported identity/account settings land in Mission 2 prompt M2-15."
    />
  );
}
