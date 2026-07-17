import { technologyPartners } from "@/data/fanora";

export default function Partners() {
  return (
    <section id="technology" className="bg-light-base dark:bg-jacarta-800">
      <div className="container">
        <div className="grid grid-cols-2 py-8 sm:grid-cols-5">
          {technologyPartners.map((partner) => (
            <div
              key={partner.id}
              className="flex min-h-[103px] flex-col items-center justify-center text-center"
            >
              <span className="font-display text-lg font-semibold text-jacarta-700 dark:text-white">
                {partner.name}
              </span>
              <span className="mt-1 text-2xs uppercase tracking-wider text-jacarta-400 dark:text-jacarta-300">
                {partner.detail}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
