import Image from "next/image";
import { fanJourney } from "@/data/fanora";

export default function Process() {
  return (
    <section id="fan-journey" className="relative py-24 text-white">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
      <div className="container">
        <h2 className="mb-16 text-center font-display text-3xl text-white">
          从加入社区到拥有链上粉丝身份
        </h2>
        <div className="grid grid-cols-1 gap-12 md:grid-cols-2 lg:grid-cols-4">
          {fanJourney.map((step) => (
            <div key={step.id} className="text-center">
              <div
                className="mb-6 inline-flex rounded-full p-3"
                style={{ backgroundColor: step.ringColor }}
              >
                <div
                  className={`inline-flex h-12 w-12 items-center justify-center rounded-full ${step.bgClass}`}
                >
                  <Image
                    width={24}
                    height={24}
                    src={step.iconSrc}
                    alt={step.title}
                  />
                </div>
              </div>
              <h3 className="mb-4 font-display text-lg text-white">
                {step.title}
              </h3>
              <p className="text-white/55">{step.description}</p>
            </div>
          ))}
        </div>

        <p className="mx-auto mt-20 max-w-2xl text-center text-lg text-white/75">
          你始终使用自己的钱包管理链上账户。登录签名不消耗 Gas，也不会授权 Fanora 转移资产；Fanora 不读取或保存私钥与助记词。
        </p>

        <div className="mx-auto mt-7 max-w-md text-center">
          <a
            href="#proof-of-fandom"
            className="inline-block w-full rounded-full bg-accent py-3 px-6 font-display text-sm text-white shadow-accent-volume transition-all hover:bg-accent-dark"
          >
            了解 Proof of Fandom
          </a>
        </div>
      </div>
    </section>
  );
}
