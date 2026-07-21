export class Web3AuthTimeoutError extends Error {
  constructor(message = "钱包确认没有完成，请重试，或改用邮箱/社交账号登录。") {
    super(message);
    this.name = "Web3AuthTimeoutError";
  }
}

export function withWeb3AuthTimeout<T>(
  action: Promise<T>,
  timeoutMs: number,
  message?: string,
) {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(() => {
      reject(new Web3AuthTimeoutError(message));
    }, timeoutMs);
  });

  return Promise.race([action, timeout]).finally(() => {
    if (timeoutId) clearTimeout(timeoutId);
  });
}
