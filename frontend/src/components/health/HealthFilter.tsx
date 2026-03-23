import { Button } from "@/components/ui/button";

type FilterMode = "all" | "problems";

interface HealthFilterProps {
  mode: FilterMode;
  onChange: (mode: FilterMode) => void;
}

export function HealthFilter({ mode, onChange }: HealthFilterProps) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Button
        variant={mode === "all" ? "default" : "outline"}
        size="sm"
        onClick={() => onChange("all")}
      >
        All
      </Button>
      <Button
        variant={mode === "problems" ? "default" : "outline"}
        size="sm"
        onClick={() => onChange("problems")}
      >
        Degraded & Failing
      </Button>
    </div>
  );
}
