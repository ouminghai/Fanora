import WalletButton from "@/components/web3/WalletButton";
import Image from "next/image";
import Link from "next/link";

export default function Login() {
  return (
    <section className="relative min-h-screen py-24 lg:flex lg:py-0">
      <div className="relative hidden w-1/2 lg:block">
        <Image
          src="/img/login.jpg"
          fill
          priority
          className="object-cover"
          alt="NFT badge artwork"
        />
      </div>

      <div className="container flex items-center lg:w-1/2">
        <div className="mx-auto w-full max-w-md py-12">
          <Link href="/" className="mb-12 inline-block">
            <Image
              src="/img/logo.png"
              width={130}
              height={28}
              className="max-h-7 dark:hidden"
              alt="NFT Badge"
            />
            <Image
              src="/img/logo_white.png"
              width={130}
              height={28}
              className="hidden max-h-7 dark:block"
              alt="NFT Badge"
            />
          </Link>

          <h1 className="mb-3 font-display text-3xl font-semibold text-jacarta-700 dark:text-white">
            Connect your wallet
          </h1>
          <p className="mb-8 text-jacarta-500 dark:text-jacarta-300">
            Choose an installed wallet or scan with WalletConnect. You remain in
            control and will approve every onchain action.
          </p>

          <WalletButton variant="login" />

          <p className="mt-5 text-sm text-jacarta-400">
            Start on Sepolia or Base Sepolia while developing. Never share your
            recovery phrase with this site or anyone else.
          </p>
        </div>
      </div>
    </section>
  );
}

