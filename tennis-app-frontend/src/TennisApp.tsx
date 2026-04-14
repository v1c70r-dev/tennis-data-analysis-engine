import { ThemeProvider } from "@/components/theme-provider"
import HomePage from "./HomePage"

export const TennisApp = () => {
  return (
    <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
      <HomePage />
    </ThemeProvider>
  )
}