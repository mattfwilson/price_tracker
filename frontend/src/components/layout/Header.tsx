import { BellDropdown } from "@/components/alerts/BellDropdown";

export function Header() {
  return (
    <header className="sticky top-0 z-50 h-12 border-b bg-background">
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <span className="font-heading text-xl font-bold">Price Scraper</span>
        <BellDropdown />
      </div>
    </header>
  );
}
