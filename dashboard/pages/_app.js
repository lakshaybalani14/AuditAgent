import Head from "next/head";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import "../styles/globals.css";
import "../styles/layout-refinement.css";
import "../styles/navbar.css";
import "../styles/workload-comparison.css";
import "../styles/policy-radar.css";
import "../styles/overview.css";
import "../styles/split-flap.css";
import "../styles/pipeline-motion.css";
import "../styles/run-trace.css";
import "../styles/animated-content.css";
export default function App({ Component, pageProps }) {
  const router = useRouter();
  const [openingPage, setOpeningPage] = useState(false);
  const [navigationError, setNavigationError] = useState(false);
  useEffect(() => {
    const start = () => { setOpeningPage(true); setNavigationError(false); };
    const complete = () => setOpeningPage(false);
    const failed = (error) => { setOpeningPage(false); if (!error.cancelled) setNavigationError(true); };
    router.events.on("routeChangeStart", start);
    router.events.on("routeChangeComplete", complete);
    router.events.on("routeChangeError", failed);
    return () => { router.events.off("routeChangeStart", start); router.events.off("routeChangeComplete", complete); router.events.off("routeChangeError", failed); };
  }, [router.events]);
  return <><Head><title>AuditAgent</title><link rel="preconnect" href="https://fonts.googleapis.com" /><link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" /><link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet" /></Head>{openingPage && <div className="route-load-indicator" role="status"><span>Opening page…</span></div>}{navigationError && <div className="route-navigation-error" role="alert">The page could not open. Please select it again.</div>}<Component {...pageProps} /></>;
}
