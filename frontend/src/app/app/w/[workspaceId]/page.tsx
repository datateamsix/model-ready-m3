import { Folder } from "lucide-react";
import { RouteStub } from "@/components/prem3/route-stub";

export default function Page() {
  return (
    <RouteStub
      icon={Folder}
      title="MMM Project"
      description="The project home (Datasets, Planning, Taskmaster, Meridian Integration status, recent activity) lands in Mission 2 prompt M2-11."
    />
  );
}
