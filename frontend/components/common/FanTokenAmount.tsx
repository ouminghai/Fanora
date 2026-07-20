import React from "react";

type FanTokenAmountProps = {
  amount: number | string;
  prefix?: string;
  showSymbol?: boolean;
  className?: string;
  iconClassName?: string;
};

export function FanTokenIcon({ className = "h-[1em] w-[0.72em]" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 36"
      className={`shrink-0 fill-current ${className}`}
      aria-hidden="true"
      focusable="false"
    >
      <path d="M12 0 0 18.2 12 25l12-6.8L12 0Z" opacity="0.9" />
      <path d="M12 27.4 0 20.6 12 36l12-15.4-12 6.8Z" opacity="0.62" />
      <path d="m12 24.9 12-6.7L12 14.8 0 18.2l12 6.7Z" opacity="0.42" />
    </svg>
  );
}

export default function FanTokenAmount({
  amount,
  prefix = "",
  showSymbol = false,
  className = "",
  iconClassName,
}: FanTokenAmountProps) {
  const formattedAmount = typeof amount === "number" ? amount.toLocaleString("en-US") : amount;
  const accessibleAmount = `${prefix}${formattedAmount} Fan Token`;

  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap ${className}`}
      aria-label={accessibleAmount}
      title="Fan Token (FAN)"
      data-fan-token-amount
    >
      <FanTokenIcon className={iconClassName} />
      <span aria-hidden="true">
        {prefix}
        {formattedAmount}
      </span>
      {showSymbol && (
        <span aria-hidden="true" className="font-medium opacity-70">
          FAN
        </span>
      )}
    </span>
  );
}
