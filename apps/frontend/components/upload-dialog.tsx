"use client";

import { useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  FileSpreadsheet,
  Loader2,
  UploadCloud,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ApiError } from "@/lib/api/client";
import { useUploadSales } from "@/lib/api/hooks";
import type { ApiErrorDetail, SalesImport } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const MAX_BYTES = 5 * 1024 * 1024;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function UploadDialog({
  locationId,
  trigger,
}: {
  locationId: string;
  trigger?: React.ReactElement;
}) {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [details, setDetails] = useState<ApiErrorDetail[] | null>(null);
  const [result, setResult] = useState<SalesImport | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const upload = useUploadSales(locationId);

  function reset() {
    setFile(null);
    setDetails(null);
    setResult(null);
    setDragActive(false);
  }

  function onOpenChange(next: boolean) {
    setOpen(next);
    if (!next) reset();
  }

  function pick(picked: File | null | undefined) {
    setDetails(null);
    setFile(picked ?? null);
  }

  async function submit() {
    if (!file) return;
    setDetails(null);
    try {
      const res = await upload.mutateAsync(file);
      setResult(res);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "invalid_sales_import" && err.details?.length) {
          setDetails(err.details);
        } else {
          toast.error(err.message);
        }
      } else {
        toast.error("Upload failed");
      }
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger render={trigger ?? <Button>Upload sales CSV</Button>} />
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="text-primary">Upload sales data</DialogTitle>
          <DialogDescription>
            Upload a CSV with columns: date, item_name, quantity, and optional revenue.
          </DialogDescription>
        </DialogHeader>

        {result ? (
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            <div className="flex size-14 items-center justify-center rounded-full bg-primary/10 text-primary">
              <CheckCircle2 className="size-7" />
            </div>
            <div className="space-y-1">
              <h3 className="font-heading text-lg font-semibold">Upload successful</h3>
              <p className="text-sm text-muted-foreground">
                Imported {(result.accepted_row_count ?? 0).toLocaleString()} rows.{" "}
                {result.forecast_generated
                  ? "Forecast updated from the new data."
                  : "Not enough recent data to forecast yet."}
              </p>
            </div>
          </div>
        ) : (
          <>
            <div
              role="button"
              tabIndex={0}
              onClick={() => inputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
              }}
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragActive(false);
                pick(e.dataTransfer.files?.[0]);
              }}
              className={cn(
                "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-8 text-center transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring",
                dragActive
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/50 hover:bg-muted/50",
              )}
            >
              {file ? (
                <div className="flex items-center gap-3">
                  <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <FileSpreadsheet className="size-5" />
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground">{formatBytes(file.size)}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      pick(null);
                    }}
                    aria-label="Remove file"
                  >
                    <X className="size-4" />
                  </Button>
                </div>
              ) : (
                <>
                  <div className="flex size-14 items-center justify-center rounded-full bg-muted text-muted-foreground">
                    <UploadCloud className="size-6" />
                  </div>
                  <p className="text-sm">
                    <span className="font-medium text-primary">Click to choose</span> or
                    drag and drop
                  </p>
                  <p className="text-xs text-muted-foreground">CSV files only (max 5 MB)</p>
                </>
              )}
              <input
                ref={inputRef}
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={(e) => pick(e.target.files?.[0])}
              />
            </div>

            {file && file.size > MAX_BYTES ? (
              <p className="text-sm text-destructive">File exceeds the 5 MB limit.</p>
            ) : null}

            {details ? (
              <div className="max-h-44 space-y-1 overflow-auto rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-xs">
                <p className="flex items-center gap-1.5 font-medium text-destructive">
                  <AlertCircle className="size-3.5" />
                  {details.length} invalid row{details.length === 1 ? "" : "s"} — nothing
                  was imported
                </p>
                <ul className="space-y-0.5 text-muted-foreground">
                  {details.map((d, i) => (
                    <li key={i}>
                      Row {d.row ?? "?"}
                      {d.field ? ` · ${d.field}` : ""}: {d.message}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </>
        )}

        <DialogFooter>
          {result ? (
            <Button onClick={() => onOpenChange(false)}>Done</Button>
          ) : (
            <>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button
                onClick={submit}
                disabled={!file || file.size > MAX_BYTES || upload.isPending}
              >
                {upload.isPending ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Uploading…
                  </>
                ) : (
                  "Upload"
                )}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
