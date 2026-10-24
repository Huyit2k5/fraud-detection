export function ComingSoon({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mx-auto mt-16 max-w-xl rounded-xl border border-line bg-panel p-6">
      <h1 className="text-lg font-semibold">{title}</h1>
      <p className="mt-2 text-sm leading-relaxed text-muted">{children}</p>
    </section>
  );
}
