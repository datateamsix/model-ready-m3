import { Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ArtifactRow } from "./artifact-row";
import type { ArtifactRef } from "@/lib/format/proof";

export function ProofDrawer({ artifacts }: { artifacts: ArtifactRef[] }) {
  return (
    <Sheet>
      <SheetTrigger
        render={
          <Button variant="outline" size="sm">
            <Eye className="size-4" aria-hidden="true" />
            View proof
          </Button>
        }
      />
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Proof</SheetTitle>
          <SheetDescription>
            Every artifact below comes directly from the run&apos;s proof bundle. Nothing here is
            calculated by the frontend.
          </SheetDescription>
        </SheetHeader>
        <div className="mt-4 px-4">
          {artifacts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No proof artifacts are available for this run yet.</p>
          ) : (
            artifacts.map((artifact, index) => (
              <ArtifactRow key={`${artifact.label}-${index}`} artifact={artifact} />
            ))
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
