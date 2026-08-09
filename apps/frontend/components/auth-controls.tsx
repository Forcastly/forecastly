"use client";

import { SignInButton, UserButton, useUser } from "@clerk/nextjs";

import { buttonVariants } from "@/components/ui/button";

/** Clerk sign-in / account controls, shown when Clerk is configured. */
export function AuthControls() {
  const { isLoaded, isSignedIn } = useUser();

  if (!isLoaded) return <div className="size-8" aria-hidden />;

  return isSignedIn ? (
    <UserButton />
  ) : (
    <SignInButton mode="modal">
      <button className={buttonVariants({ size: "sm" })}>Sign in</button>
    </SignInButton>
  );
}
