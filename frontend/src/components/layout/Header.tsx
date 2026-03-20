import { BellDropdown } from "@/components/alerts/BellDropdown";
import { ThemeToggle } from "./ThemeToggle";

export function Header() {
  return (
    <header className="sticky top-0 z-50 h-12 border-b border-border/60 bg-background/75 backdrop-blur-md">
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <span className="font-heading text-xl font-bold tracking-tight">
          <span className="text-primary">Price</span>
          <span className="text-foreground/90"> Scraper</span>
        </span>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <BellDropdown />
        </div>
      </div>
    </header>
  );
}
