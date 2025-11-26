import { cn, getStatusColor } from '@/lib/utils';

interface StatusBadgeProps {
  status: string;
  variant?: 'default' | 'dot';
  className?: string;
}

export default function StatusBadge({ status, variant = 'default', className }: StatusBadgeProps) {
  if (variant === 'dot') {
    return (
      <div className={cn("flex items-center space-x-2", className)}>
        <div className={cn("w-2 h-2 rounded-full", getStatusColor(status).split(' ')[0])} />
        <span className="text-sm capitalize">{status}</span>
      </div>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border capitalize",
        getStatusColor(status),
        className
      )}
    >
      {status}
    </span>
  );
}