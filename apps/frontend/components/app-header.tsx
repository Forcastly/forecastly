import Link from "next/link";

import { DevUserSwitcher } from "@/components/dev-user-switcher";

export function AppHeader() {
  return (
    <header className="border-b">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/" className="font-heading text-lg font-semibold">
          Forecastly
        </Link>
        <DevUserSwitcher />
      </div>
    </header>
  );
}
