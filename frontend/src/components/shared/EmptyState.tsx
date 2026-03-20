import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  heading: string;
  body: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ heading, body, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <h2 className="font-heading text-lg font-bold">{heading}</h2>
      <p className="mt-2 text-sm text-muted-foreground">{body}</p>
      {action && (
        <Button className="mt-6" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}
