"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DEV_USERS, useDevUser } from "@/lib/dev-user";

export function DevUserSwitcher() {
  const { subject, setSubject } = useDevUser();

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground">Dev user</span>
      <Select value={subject} onValueChange={(value) => value && setSubject(value)}>
        <SelectTrigger size="sm" className="w-40">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {DEV_USERS.map((user) => (
            <SelectItem key={user} value={user}>
              {user}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
