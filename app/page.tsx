import { Suspense } from "react";
import { Explorer } from "@/components/explorer";
export default function Page() {
  return (
    <Suspense
      fallback={<div className="initial-loading">Abriendo observatorio…</div>}
    >
      <Explorer />
    </Suspense>
  );
}
