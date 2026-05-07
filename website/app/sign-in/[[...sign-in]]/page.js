import { SignIn } from "@clerk/nextjs";

export const metadata = {
  title: "Sign In",
};

export default function SignInPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-background py-16 px-4">
      <SignIn
        appearance={{
          elements: {
            card: "shadow-none border border-border rounded-lg",
            headerTitle: "text-foreground font-semibold",
            headerSubtitle: "text-muted-foreground",
            socialButtonsBlockButton: "border border-border text-foreground hover:bg-accent",
            formFieldInput: "border border-input bg-background text-foreground",
            footerActionLink: "text-primary",
            formButtonPrimary: "bg-[#185FA5] hover:opacity-90",
          },
        }}
      />
    </main>
  );
}
