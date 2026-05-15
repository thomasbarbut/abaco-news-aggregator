export default function ArticleCardSkeleton() {
  return (
    <div className="flex gap-4 px-5 py-4 border-b border-gray-100 dark:border-gray-800">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-2">
          <div className="skeleton h-4 w-20" />
          <div className="skeleton h-3 w-16" />
        </div>
        <div className="skeleton h-5 w-4/5 mb-1.5" />
        <div className="skeleton h-4 w-full mb-1" />
        <div className="skeleton h-4 w-3/4" />
      </div>
      <div className="skeleton w-24 h-20 sm:w-32 sm:h-24 rounded-lg shrink-0" />
    </div>
  );
}
