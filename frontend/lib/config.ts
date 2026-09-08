/** NEXT_PUBLIC_API_BASE_URL is compiled into the client; container runtime cannot change it. */
export function resolveApiBaseUrl(value: string | undefined): string {
  const base = (value ?? "http://localhost:8000/api/v1").trim().replace(/\/+$/, "");
  if (base.startsWith("/") && !base.startsWith("//") && !/[?#\\]/.test(base)) return base;
  let url: URL;
  try { url = new URL(base); } catch { throw new Error("NEXT_PUBLIC_API_BASE_URL must be an http(s) URL or same-origin path."); }
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must not contain credentials, queries or fragments.");
  }
  return base;
}
export const API_BASE_URL = resolveApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
