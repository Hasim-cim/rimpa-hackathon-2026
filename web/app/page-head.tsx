/** Title and one-line "what this page is for", the same on every page. */
export default function PageHead({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="page-head">
      <h1>{title}</h1>
      <p>{children}</p>
    </div>
  );
}
