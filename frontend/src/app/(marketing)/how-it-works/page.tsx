import { BookOpen } from "lucide-react";
import { RouteStub } from "@/components/prem3/route-stub";

export default function Page() {
  return (
    <RouteStub
      icon={BookOpen}
      title="How it works"
      description="The Project -> Dataset -> Evaluation lifecycle and Map/Mend/Validate/Meridian EDA story lands in Mission 2 prompt M2-04."
    />
  );
}
