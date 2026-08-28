import React from "react";
import { Moon, Sun, Monitor } from "lucide-react";
import { useTheme } from "../contexts/ThemeContext";
import { Button } from "./ui/button";
import { motion, AnimatePresence } from "framer-motion";

export const ThemeToggle: React.FC = () => {
  const { theme, setTheme } = useTheme();

  const themes: { name: "light" | "dark" | "system"; icon: typeof Sun }[] = [
    { name: "light", icon: Sun },
    { name: "dark", icon: Moon },
    { name: "system", icon: Monitor },
  ];

  return (
    <div className="flex items-center bg-muted/50 p-1 rounded-xl border border-border/50">
      {themes.map(({ name, icon: Icon }) => (
        <Button
          key={name}
          variant="ghost"
          size="sm"
          onClick={() => setTheme(name)}
          className={`relative h-8 w-8 p-0 rounded-lg transition-all duration-300 ${
            theme === name
              ? "text-primary bg-background shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Icon className="h-4 w-4 relative z-10" />
          {theme === name && (
            <motion.div
              layoutId="activeTheme"
              className="absolute inset-0 bg-background rounded-lg shadow-sm"
              transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
            />
          )}
        </Button>
      ))}
    </div>
  );
};

export const ThemeToggleCompact: React.FC = () => {
  const { theme, setTheme } = useTheme();

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="h-10 w-10 rounded-xl hover:bg-accent/10 hover:text-accent group"
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={theme}
          initial={{ y: -20, opacity: 0, rotate: -90 }}
          animate={{ y: 0, opacity: 1, rotate: 0 }}
          exit={{ y: 20, opacity: 0, rotate: 90 }}
          transition={{ duration: 0.2 }}
        >
          {theme === "dark" ? (
            <Moon className="h-5 w-5 text-indigo-400" />
          ) : (
            <Sun className="h-5 w-5 text-amber-500" />
          )}
        </motion.div>
      </AnimatePresence>
      <span className="sr-only">Toggle theme</span>
    </Button>
  );
};
