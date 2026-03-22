import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCreateWatchQuery,
  useUpdateWatchQuery,
} from "@/hooks/use-watch-queries";
import { Loader2, Plus, X } from "lucide-react";
import type { WatchQueryDetailResponse } from "@/types/api";

interface QueryFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editQuery?: WatchQueryDetailResponse | null;
}

interface FormErrors {
  name?: string;
  threshold?: string;
  pctDrop?: string;
  cooldown?: string;
  urls?: string;
  urlErrors?: Record<number, string>;
}

const SCHEDULE_OPTIONS = [
  { value: "every_1h", label: "Every 1 hour" },
  { value: "every_3h", label: "Every 3 hours" },
  { value: "every_6h", label: "Every 6 hours" },
  { value: "every_12h", label: "Every 12 hours" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
];

export function QueryFormDialog({
  open,
  onOpenChange,
  editQuery,
}: QueryFormDialogProps) {
  const [name, setName] = useState("");
  const [threshold, setThreshold] = useState("");
  const [schedule, setSchedule] = useState("daily");
  const [urls, setUrls] = useState<string[]>([""]);
  const [pctDrop, setPctDrop] = useState("");
  const [cooldownHours, setCooldownHours] = useState("24");
  const [errors, setErrors] = useState<FormErrors>({});

  const createMutation = useCreateWatchQuery();
  const updateMutation = useUpdateWatchQuery();

  const isEditing = !!editQuery;
  const isPending = createMutation.isPending || updateMutation.isPending;

  // Reset form when editQuery changes or dialog opens
  useEffect(() => {
    if (open) {
      if (editQuery) {
        setName(editQuery.name);
        setThreshold((editQuery.threshold_cents / 100).toFixed(2));
        setSchedule(editQuery.schedule);
        setUrls(
          editQuery.retailer_urls.length > 0
            ? editQuery.retailer_urls.map((u) => u.url)
            : [""]
        );
        setPctDrop(editQuery.pct_drop_threshold != null ? String(editQuery.pct_drop_threshold) : "");
        setCooldownHours(String(editQuery.alert_cooldown_hours));
      } else {
        setName("");
        setThreshold("");
        setSchedule("daily");
        setUrls([""]);
        setPctDrop("");
        setCooldownHours("24");
      }
      setErrors({});
    }
  }, [editQuery?.id, open]);

  function validate(): boolean {
    const newErrors: FormErrors = {};

    if (name.trim() === "") {
      newErrors.name = "Query name is required";
    }

    if (
      threshold === "" ||
      isNaN(parseFloat(threshold)) ||
      parseFloat(threshold) <= 0
    ) {
      newErrors.threshold = "Enter a valid dollar amount (e.g. 400.00)";
    }

    if (pctDrop.trim() !== "") {
      const pctVal = parseFloat(pctDrop);
      if (isNaN(pctVal) || pctVal <= 0 || pctVal > 100) {
        newErrors.pctDrop = "Enter a value between 0 and 100, or leave empty to disable";
      }
    }

    const cooldownVal = parseInt(cooldownHours, 10);
    if (isNaN(cooldownVal) || cooldownVal < 0) {
      newErrors.cooldown = "Enter 0 or more hours";
    }

    const cleanUrls = urls.filter((u) => u.trim() !== "");
    if (cleanUrls.length === 0) {
      newErrors.urls = "At least one retailer URL is required";
    }

    const urlErrors: Record<number, string> = {};
    urls.forEach((u, i) => {
      if (u.trim() !== "" && !u.trim().startsWith("https://")) {
        urlErrors[i] = "Enter a valid URL starting with https://";
      }
    });
    if (Object.keys(urlErrors).length > 0) {
      newErrors.urlErrors = urlErrors;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    const thresholdCents = Math.round(parseFloat(threshold) * 100);
    const cleanUrls = urls.filter((u) => u.trim() !== "").map((u) => u.trim());

    try {
      if (isEditing && editQuery) {
        await updateMutation.mutateAsync({
          id: editQuery.id,
          data: {
            name: name.trim(),
            threshold_cents: thresholdCents,
            schedule,
            urls: cleanUrls,
            pct_drop_threshold: pctDrop.trim() !== "" ? parseFloat(pctDrop) : null,
            alert_cooldown_hours: parseInt(cooldownHours, 10),
          },
        });
      } else {
        await createMutation.mutateAsync({
          name: name.trim(),
          threshold_cents: thresholdCents,
          urls: cleanUrls,
          schedule,
          pct_drop_threshold: pctDrop.trim() !== "" ? parseFloat(pctDrop) : null,
          alert_cooldown_hours: parseInt(cooldownHours, 10),
        });
      }
      onOpenChange(false);
    } catch {
      // Error handled by TanStack Query
    }
  }

  function updateUrl(index: number, value: string) {
    const newUrls = [...urls];
    newUrls[index] = value;
    setUrls(newUrls);
  }

  function removeUrl(index: number) {
    if (urls.length <= 1) return;
    setUrls(urls.filter((_, i) => i !== index));
  }

  function addUrl() {
    setUrls([...urls, ""]);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle className="font-heading">
            {isEditing ? "Edit Query" : "Create Query"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="query-name">Name</Label>
            <Input
              id="query-name"
              type="text"
              placeholder="e.g. MacBook Pro 16"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name}</p>
            )}
          </div>

          {/* Price Threshold */}
          <div className="space-y-2">
            <Label htmlFor="query-threshold">Price Threshold</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">
                $
              </span>
              <Input
                id="query-threshold"
                type="text"
                inputMode="decimal"
                placeholder="400.00"
                className="pl-7"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
              />
            </div>
            {errors.threshold && (
              <p className="text-sm text-destructive">{errors.threshold}</p>
            )}
          </div>

          {/* Schedule */}
          <div className="space-y-2">
            <Label htmlFor="query-schedule">Schedule</Label>
            <Select value={schedule} onValueChange={setSchedule}>
              <SelectTrigger id="query-schedule">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SCHEDULE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Percentage Drop Threshold - optional */}
          <div className="space-y-2">
            <Label htmlFor="query-pct-drop">Price Drop Alert (%)</Label>
            <Input
              id="query-pct-drop"
              type="text"
              inputMode="decimal"
              placeholder="e.g. 10 (leave empty to disable)"
              value={pctDrop}
              onChange={(e) => setPctDrop(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Alert when price drops this % below 30-day average
            </p>
            {errors.pctDrop && (
              <p className="text-sm text-destructive">{errors.pctDrop}</p>
            )}
          </div>

          {/* Alert Cooldown */}
          <div className="space-y-2">
            <Label htmlFor="query-cooldown">Alert Cooldown (hours)</Label>
            <Input
              id="query-cooldown"
              type="number"
              min="0"
              value={cooldownHours}
              onChange={(e) => setCooldownHours(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Suppress repeat alerts within this time window (0 to disable)
            </p>
            {errors.cooldown && (
              <p className="text-sm text-destructive">{errors.cooldown}</p>
            )}
          </div>

          {/* Retailer URLs */}
          <div className="space-y-2">
            <Label>Retailer URLs</Label>
            {urls.map((url, index) => (
              <div key={index} className="space-y-1">
                <div className="flex items-center gap-2">
                  <Input
                    type="text"
                    placeholder="https://www.example.com/product"
                    value={url}
                    onChange={(e) => updateUrl(index, e.target.value)}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => removeUrl(index)}
                    disabled={urls.length <= 1}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
                {errors.urlErrors?.[index] && (
                  <p className="text-sm text-destructive">
                    {errors.urlErrors[index]}
                  </p>
                )}
              </div>
            ))}
            {errors.urls && (
              <p className="text-sm text-destructive">{errors.urls}</p>
            )}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addUrl}
            >
              <Plus className="h-4 w-4 mr-1" />
              Add URL
            </Button>
          </div>

          <DialogFooter>
            <Button type="submit" disabled={isPending}>
              {isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {isEditing ? "Save Changes" : "Create Query"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
