export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center space-y-4">
        <h2 className="text-4xl font-bold text-white">404</h2>
        <p className="text-syn-muted">Page not found.</p>
        <a
          href="/"
          className="inline-block px-4 py-2 bg-syn-accent text-white rounded-lg hover:bg-syn-accent-hover transition-colors"
        >
          Back to home
        </a>
      </div>
    </div>
  );
}
