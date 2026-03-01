import { cn } from "@/lib/utils"

function Skeleton({ className, ref, ...props }: React.ComponentPropsWithRef<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("bg-accent animate-pulse rounded-md", className)}
      {...props}
    />
  )
}

export { Skeleton }
