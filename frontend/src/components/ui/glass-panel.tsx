import { cn } from "@/lib/utils";

interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  glow?: "cyan" | "green" | "orange" | "red" | "none";
}

export function GlassPanel({
  className,
  glow = "none",
  children,
  ...props
}: GlassPanelProps) {
  return (
    <div
      className={cn(
        "glass-panel rounded-lg p-4",
        glow === "cyan" && "glow-cyan",
        glow === "green" && "glow-green",
        glow === "orange" && "glow-orange",
        glow === "red" && "glow-red",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
