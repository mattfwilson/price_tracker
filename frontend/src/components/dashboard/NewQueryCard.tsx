import { Plus } from "lucide-react";
import { Card } from "@/components/ui/card";

interface NewQueryCardProps {
  onClick: () => void;
}

export function NewQueryCard({ onClick }: NewQueryCardProps) {
  return (
    <Card
      className="flex min-h-[200px] cursor-pointer items-center justify-center border-2 border-dashed hover:border-solid"
      onClick={onClick}
    >
      <div className="flex flex-col items-center gap-2 text-muted-foreground">
        <Plus className="h-8 w-8" />
        <span className="text-sm font-medium">Add Query</span>
      </div>
    </Card>
  );
}
