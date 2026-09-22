import Link from "next/link";
import { ArrowUpRight, ShieldCheck } from "lucide-react";
import { API_BASE_URL } from "@/lib/config";

export function SiteHeader() {
  return (
    <header className="site-header">
      <Link className="site-brand" href="/" aria-label="OpsGuard AI home"><span className="brand-icon"><ShieldCheck size={22} /></span><span>OPSGUARD<span className="brand-ai"> / AI</span><small>SECURITY OPERATIONS CONSOLE</small></span></Link>
      <div className="header-system"><span className="header-separator">/</span><span>RETRIEVE<span className="text-accent"> → </span>INVESTIGATE<span className="text-accent"> → </span>REVIEW</span></div>
      <a className="header-api" href={`${API_BASE_URL}/health`} rel="noreferrer" target="_blank">API HEALTH <ArrowUpRight size={13} /></a>
    </header>
  );
}
