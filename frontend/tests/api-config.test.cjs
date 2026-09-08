const test = require("node:test");
const assert = require("node:assert/strict");
const { join } = require("node:path");
const { resolveApiBaseUrl } = require(join(process.env.OPSGUARD_TEST_BUILD_DIRECTORY, "lib/config.js"));
test("public API build configuration accepts explicit absolute or same-origin URLs", () => {
  assert.equal(resolveApiBaseUrl(undefined), "http://localhost:8000/api/v1");
  assert.equal(resolveApiBaseUrl("https://example.test/api/v1/"), "https://example.test/api/v1");
  assert.equal(resolveApiBaseUrl("/api/v1"), "/api/v1");
  for (const value of ["", "//example.test/api", "file:///etc/passwd", "https://user:secret@example.test", "http://localhost:8000?secret=1"]) {
    assert.throws(() => resolveApiBaseUrl(value), /NEXT_PUBLIC_API_BASE_URL/);
  }
});
