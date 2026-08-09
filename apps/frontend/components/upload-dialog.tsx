"use client";

import { useState } from "react";
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
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api/client";
import { useUploadSales } from "@/lib/api/hooks";
import type { ApiErrorDetail } from "@/lib/api/types";

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
  const upload = useUploadSales(locationId);

  async function submit() {
    if (!file) return;
    setDetails(null);
    try {
      const result = await upload.mutateAsync(file);
      toast.success(`Imported ${result.accepted_row_count ?? 0} rows`, {
        description: result.forecast_generated
          ? "Forecast updated from the new data."
          : "Not enough recent data to forecast yet.",
      });
      setOpen(false);
      setFile(null);
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
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={trigger ?? <Button>Upload sales CSV</Button>} />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload sales CSV</DialogTitle>
          <DialogDescription>
            Columns: date, item_name, quantity, revenue (optional).
          </DialogDescription>
        </DialogHeader>

        <Input
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => {
            setDetails(null);
            setFile(e.target.files?.[0] ?? null);
          }}
        />

        {details ? (
          <div className="max-h-40 overflow-auto rounded-md border p-2 text-xs">
            <p className="mb-1 font-medium text-destructive">Invalid rows</p>
            <ul className="space-y-0.5">
              {details.map((d, i) => (
                <li key={i}>
                  Row {d.row ?? "?"}
                  {d.field ? ` · ${d.field}` : ""}: {d.message}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={!file || upload.isPending}>
            {upload.isPending ? "Uploading…" : "Upload"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
