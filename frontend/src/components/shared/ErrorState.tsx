import { AlertCircle } from "lucide-react";

interface ErrorStateProps {
  message?: string;
}

export function ErrorState({
  message = "Something went wrong. Check that the backend is running and try again.",
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <AlertCircle className="h-10 w-10 text-destructive" />
      <p className="mt-4 text-sm text-muted-foreground">{message}</p>
    </div>
  );
}
