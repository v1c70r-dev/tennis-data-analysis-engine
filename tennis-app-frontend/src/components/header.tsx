import { Circle, Settings, User } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export function Header() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-card px-6">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
          <Circle className="h-5 w-5 fill-primary-foreground text-primary-foreground" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-foreground">Tennis Analyzer</h1>
        </div>
      </div>

      <nav className="hidden items-center gap-6 md:flex">
        <a href="#" className="text-sm font-medium text-primary">
          Dashboard
        </a>
        <a href="#" className="text-sm text-muted-foreground transition-colors hover:text-foreground">
          My Matches
        </a>
        <a href="#" className="text-sm text-muted-foreground transition-colors hover:text-foreground">
          Analytics
        </a>
        <a href="#" className="text-sm text-muted-foreground transition-colors hover:text-foreground">
          Settings
        </a>
      </nav>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" className="h-9 w-9 text-muted-foreground hover:text-foreground">
          <Settings className="h-5 w-5" />
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full bg-secondary text-foreground">
              <User className="h-5 w-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>Profile</DropdownMenuItem>
            <DropdownMenuItem>Subscription</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Sign Out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
