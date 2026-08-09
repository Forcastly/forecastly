import Link from "next/link";

import { AuthControls } from "@/components/auth-controls";
import { DevUserSwitcher } from "@/components/dev-user-switcher";

const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

export function AppHeader() {
  return (
    <header className="border-b">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link
          href="/"
          className="font-heading text-lg font-semibold tracking-tight text-primary"
        >
          Forecastly
        </Link>
        {clerkEnabled ? <AuthControls /> : <DevUserSwitcher />}
      </div>
    </header>
  );
}
