/**
 * Skeleton loading components for better UX during data fetching.
 */

interface SkeletonProps {
  className?: string
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-gray-200 rounded ${className}`}
    />
  )
}

export function SkeletonText({ lines = 1, className = '' }: { lines?: number; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={`h-4 ${i === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full'}`}
        />
      ))}
    </div>
  )
}

export function SkeletonCard({ className = '' }: SkeletonProps) {
  return (
    <div className={`card p-4 ${className}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <Skeleton className="h-5 w-1/3 mb-2" />
          <SkeletonText lines={2} />
        </div>
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
    </div>
  )
}

export function SkeletonTimeEntry() {
  return (
    <div className="card p-3">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Skeleton className="h-5 w-10" />
            <Skeleton className="h-5 w-24" />
          </div>
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="flex gap-1">
          <Skeleton className="h-8 w-8 rounded" />
          <Skeleton className="h-8 w-8 rounded" />
        </div>
      </div>
    </div>
  )
}

export function SkeletonTimesheetList() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}

export function SkeletonDashboard() {
  return (
    <div className="space-y-6">
      {/* Summary card */}
      <div className="card p-4">
        <div className="text-center mb-2">
          <Skeleton className="h-10 w-16 mx-auto mb-2" />
          <Skeleton className="h-4 w-24 mx-auto" />
        </div>
        <div className="flex justify-center gap-4 border-t pt-2">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-20" />
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <Skeleton className="h-10 flex-1 rounded-lg" />
        <Skeleton className="h-10 flex-1 rounded-lg" />
      </div>

      {/* Entries */}
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <SkeletonTimeEntry key={i} />
        ))}
      </div>
    </div>
  )
}

export function SkeletonForm() {
  return (
    <div className="space-y-4">
      <div>
        <Skeleton className="h-4 w-16 mb-2" />
        <Skeleton className="h-10 w-full rounded-lg" />
      </div>
      <div>
        <Skeleton className="h-4 w-20 mb-2" />
        <div className="grid grid-cols-4 gap-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-12 rounded-lg" />
          ))}
        </div>
      </div>
      <div>
        <Skeleton className="h-4 w-24 mb-2" />
        <Skeleton className="h-10 w-full rounded-lg" />
      </div>
      <Skeleton className="h-12 w-full rounded-lg" />
    </div>
  )
}
