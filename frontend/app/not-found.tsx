import Link from "next/link";

import Footer1 from "@/components/footer/Footer1";
import Header3 from "@/components/headers/Header3";

export const metadata = {
  title: "Page not found | Fanora Protocol",
};
export default function NotFoundPage() {
  return (
    <>
      <Header3 />
      <main className="flex min-h-[70vh] items-center bg-light-base pt-28 dark:bg-jacarta-900">
        <div className="container text-center">
          <span className="font-display text-sm uppercase tracking-[0.3em] text-accent">404</span>
          <h1 className="mt-4 font-display text-5xl text-jacarta-700 dark:text-white">This identity path does not exist.</h1>
          <p className="mx-auto mt-5 max-w-xl text-lg dark:text-jacarta-300">
            Return to Fanora and continue building verifiable relationships with the communities you support.
          </p>
          <Link href="/" className="mt-8 inline-block rounded-full bg-accent px-8 py-3 font-semibold text-white shadow-accent-volume hover:bg-accent-dark">
            Back to Fanora
          </Link>
        </div>
      </main>
      <Footer1 />
    </>
  );
}
