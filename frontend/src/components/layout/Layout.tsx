import { Outlet } from "react-router-dom";
import { Header } from "./Header";
import { useAlertSSE } from "@/hooks/use-sse";

export function Layout() {
  useAlertSSE();

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </>
  );
}
