import Image from "next/image";
import Link from "next/link";

export default function Cta() {
  return (
    <div className="relative z-10 -mt-48 dark:bg-jacarta-900">
      <div className="container">
        <div className="relative overflow-hidden rounded-2.5xl px-16 pt-16 pb-8 shadow-md lg:px-24">
          <picture className="pointer-events-none absolute inset-0 -z-10 dark:hidden">
            <Image
              width={1920}
              height={789}
              src="/img/gradient_light.jpg"
              priority
              alt="gradient"
              className="h-full w-full"
            />
          </picture>
          <picture className="pointer-events-none absolute inset-0 -z-10 hidden dark:block">
            <Image
              width={1920}
              height={900}
              src="/img/gradient_dark.jpg"
              alt="gradient dark"
              className="h-full w-full"
            />
          </picture>
          <div className="items-center justify-between md:flex">
            <div className="mb-6 md:w-1/2">
              <h2 className="mb-4 font-display text-2xl text-jacarta-700 dark:text-white sm:text-3xl">
                Would you like some help getting started?
              </h2>
              <p className="mb-8 text-lg dark:text-jacarta-300">
                Our support heroes will have you up and running in less than
                10mins.
              </p>
              <Link
                href="/contact"
                className="inline-block rounded-full bg-accent py-3 px-8 text-center font-semibold text-white shadow-accent-volume transition-all hover:bg-accent-dark"
              >
                Schedule a Call
              </Link>
            </div>
            <Image
              width={340}
              height={300}
              src="/img/crypto-consultant/cta_illustration.png"
              alt="image"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
