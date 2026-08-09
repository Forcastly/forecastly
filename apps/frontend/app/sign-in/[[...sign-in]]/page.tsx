import { SignIn } from "@clerk/nextjs";

const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

export default function SignInPage() {
  if (!clerkEnabled) return null;
  return (
    <div className="flex justify-center py-12">
      <SignIn />
    </div>
  );
}
