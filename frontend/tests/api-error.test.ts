import assert from "node:assert/strict";
import test from "node:test";
import { apiErrorMessage } from "../lib/api/errors";

test("422 validation details become readable modal text", () => {
  const error = {
    isAxiosError: true,
    response: {
      status: 422,
      data: {
        detail: [
          { loc: ["body", "title"], msg: "Field required", type: "missing" },
          { loc: ["body", "body"], msg: "String should have at least 2 characters", type: "string_too_short" },
        ],
      },
    },
  };

  assert.equal(apiErrorMessage(error), "title：Field required\nbody：String should have at least 2 characters");
});

test("custom backend validation errors and fallback messages stay readable", () => {
  const customError = {
    isAxiosError: true,
    response: { status: 422, data: { detail: "内容与社区主题不够相关。" } },
  };
  const malformedError = {
    isAxiosError: true,
    response: { status: 422, data: { detail: { reason: "unknown" } } },
  };

  assert.equal(apiErrorMessage(customError), "内容与社区主题不够相关。");
  assert.equal(apiErrorMessage(malformedError, "请检查提交内容。"), "请检查提交内容。");
});
