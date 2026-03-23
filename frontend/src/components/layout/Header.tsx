import { NavLink } from "react-router-dom";
import { BellDropdown } from "@/components/alerts/BellDropdown";
import { ThemeToggle } from "./ThemeToggle";
import { cn } from "@/lib/utils";

export function Header() {
  return (
    <header className="sticky top-0 z-50 h-12 border-b border-border/60 bg-background/75 backdrop-blur-md">
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center">
          <span className="font-heading text-xl font-bold tracking-tight">
            <span className="text-primary">Price</span>
            <span className="text-foreground/90"> Scraper</span>
          </span>
          <nav className="flex items-center gap-4 ml-8">
            <NavLink
              to="/health"
              className={({ isActive }) =>
                cn(
                  "text-sm font-medium transition-colors hover:text-foreground",
                  isActive ? "text-foreground" : "text-muted-foreground"
                )
              }
            >
              Health
            </NavLink>
          </nav>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <BellDropdown />
        </div>
      </div>
    </header>
  );
}
