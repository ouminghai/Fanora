import type { DailyCheckInStatus } from "@/lib/api/types";

type CheckInCalendarProps = {
  checkIn: DailyCheckInStatus | null;
};

const weekdayLabels = ["一", "二", "三", "四", "五", "六", "日"];

function pad(value: number) {
  return String(value).padStart(2, "0");
}

export default function CheckInCalendar({ checkIn }: CheckInCalendarProps) {
  const now = new Date();
  const fallbackMonth = `${now.getFullYear()}-${pad(now.getMonth() + 1)}`;
  const month = checkIn?.month || fallbackMonth;
  const [year, monthNumber] = month.split("-").map(Number);
  const daysInMonth = new Date(year, monthNumber, 0).getDate();
  const firstWeekday = (new Date(year, monthNumber - 1, 1).getDay() + 6) % 7;
  const recordByDate = new Map(
    (checkIn?.monthly_records || []).map((record) => [record.check_in_date, record.reward_fan_tokens]),
  );
  const todayKey = checkIn?.check_in_date || `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  const cells: Array<number | null> = [
    ...Array.from({ length: firstWeekday }, () => null),
    ...Array.from({ length: daysInMonth }, (_, index) => index + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  const monthLabel = new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long" }).format(
    new Date(year, monthNumber - 1, 1),
  );

  return (
    <div className="rounded-lg border border-jacarta-100 bg-jacarta-50/70 p-5 dark:border-white/10 dark:bg-white/[.035] md:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-jacarta-400">签到记录</p>
          <h3 className="mt-1 font-display text-lg font-semibold text-jacarta-700 dark:text-white">
            {monthLabel}
          </h3>
        </div>
        <div className="text-right">
          <p className="text-xs text-jacarta-400">本月签到奖励</p>
          <p className="mt-1 font-display text-xl font-semibold text-accent">
            {checkIn?.monthly_reward_fan_tokens || 0} FAN
          </p>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-7 gap-2 text-center text-[11px] font-semibold text-jacarta-400">
        {weekdayLabels.map((label) => <span key={label}>{label}</span>)}
      </div>
      <div className="mt-2 grid grid-cols-7 gap-2">
        {cells.map((day, index) => {
          if (day === null) return <span key={`empty-${index}`} className="aspect-square" />;
          const dateKey = `${year}-${pad(monthNumber)}-${pad(day)}`;
          const reward = recordByDate.get(dateKey);
          const checked = reward !== undefined;
          const isToday = dateKey === todayKey;
          const isFuture = dateKey > todayKey;

          return (
            <span
              key={dateKey}
              title={checked ? `${dateKey} 已签到，获得 ${reward} FAN` : `${dateKey} 未签到`}
              className={`flex aspect-square min-h-8 items-center justify-center rounded-md border text-xs font-semibold transition-colors ${
                checked
                  ? "border-[#18a96f] bg-[#22c884] text-white"
                  : isFuture
                    ? "border-jacarta-100 bg-white/35 text-jacarta-300 dark:border-white/[.05] dark:bg-white/[.025] dark:text-white/20"
                    : "border-jacarta-100 bg-white text-jacarta-500 dark:border-white/10 dark:bg-white/[.06] dark:text-white/55"
              } ${isToday ? "ring-2 ring-accent ring-offset-2 ring-offset-white dark:ring-offset-jacarta-800" : ""}`}
            >
              {day}
            </span>
          );
        })}
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 text-xs text-jacarta-400">
        <span>{recordByDate.size} 天已签到</span>
        <span className="inline-flex items-center gap-2">
          <span className="h-3 w-3 rounded-sm border border-jacarta-100 bg-white dark:border-white/10 dark:bg-white/[.06]" />
          未签到
          <span className="h-3 w-3 rounded-sm bg-[#22c884]" />
          已签到
        </span>
      </div>
    </div>
  );
}
