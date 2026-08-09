"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { SalesTable } from "@/components/sales-table";

export default function SalesPage() {
  const { locationId } = useParams<{ locationId: string }>();

  return (
    <div className="space-y-4">
      <div>
        <Link
          href={`/locations/${locationId}`}
          className="text-xs text-muted-foreground hover:underline"
        >
          ← Dashboard
        </Link>
        <h1 className="text-xl font-semibold">Historical sales</h1>
      </div>
      <SalesTable locationId={locationId} />
    </div>
  );
}
