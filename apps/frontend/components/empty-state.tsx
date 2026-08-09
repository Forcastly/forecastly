import type { ReactNode } from "react";

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mx-auto flex max-w-lg flex-col items-center justify-center gap-5 rounded-2xl border bg-card p-10 text-center shadow-sm sm:p-14">
      {icon ? (
        <div className="flex size-16 items-center justify-center rounded-2xl bg-primary/10 text-accent-amber">
          {icon}
        </div>
      ) : null}
      <div className="space-y-2">
        <h2 className="font-heading text-2xl font-semibold tracking-tight text-foreground">
          {title}
        </h2>
        {description ? (
          <p className="text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {action}
    </div>
  );
}
