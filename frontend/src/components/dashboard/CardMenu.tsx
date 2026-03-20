import { MoreHorizontal, Pencil, Pause, Play, RefreshCw, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { usePauseQuery, useResumeQuery } from "@/hooks/use-watch-queries";

interface CardMenuProps {
  queryId: number;
  queryName: string;
  isActive: boolean;
  onEdit: () => void;
  onScrapeNow: () => void;
  onDelete: () => void;
}

export function CardMenu({
  queryId,
  queryName,
  isActive,
  onEdit,
  onScrapeNow,
  onDelete,
}: CardMenuProps) {
  const pauseMutation = usePauseQuery();
  const resumeMutation = useResumeQuery();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          onClick={(e) => e.stopPropagation()}
          aria-label={`Actions for ${queryName}`}
        >
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={onEdit}>
          <Pencil className="h-4 w-4" />
          Edit
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => {
            if (isActive) {
              pauseMutation.mutate(queryId);
            } else {
              resumeMutation.mutate(queryId);
            }
          }}
        >
          {isActive ? (
            <>
              <Pause className="h-4 w-4" />
              Pause
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Resume
            </>
          )}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={onScrapeNow}>
          <RefreshCw className="h-4 w-4" />
          Scrape Now
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem className="text-destructive" onClick={onDelete}>
          <Trash2 className="h-4 w-4" />
          Delete
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
