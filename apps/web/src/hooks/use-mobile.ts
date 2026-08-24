import * as React from "react";

const MOBILE_BREAKPOINT = 768;

export function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState(false);

  React.useEffect(() => {
    const mediaQuery = window.matchMedia(
      `(max-width: ${MOBILE_BREAKPOINT - 1}px)`,
    );
    const syncViewport = () => setIsMobile(mediaQuery.matches);
    const syncAfterHydration = window.setTimeout(syncViewport, 0);

    mediaQuery.addEventListener("change", syncViewport);

    return () => {
      window.clearTimeout(syncAfterHydration);
      mediaQuery.removeEventListener("change", syncViewport);
    };
  }, []);

  return isMobile;
}
