export default function SkillLoading() {
  return (
    <div className="min-h-screen bg-[color:var(--surface-0)] px-6 py-28 sm:px-10">
      <div className="mx-auto max-w-6xl">
        <div className="h-3 w-40 animate-pulse bg-white/16" />
        <div className="mt-10 h-16 w-full max-w-3xl animate-pulse bg-white/12" />
        <div className="mt-5 h-16 w-full max-w-2xl animate-pulse bg-white/10" />
        <div className="mt-16 grid gap-8 lg:grid-cols-[16rem_1fr]">
          <div className="h-64 animate-pulse border-y border-white/12 bg-white/[0.03]" />
          <div className="space-y-6">
            <div className="h-32 animate-pulse border-y border-white/12 bg-white/[0.03]" />
            <div className="h-56 animate-pulse border-y border-white/12 bg-white/[0.03]" />
            <div className="h-56 animate-pulse border-y border-white/12 bg-white/[0.03]" />
          </div>
        </div>
      </div>
    </div>
  );
}
