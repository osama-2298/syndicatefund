export interface FilterOption {
  key: string | null;
  label: string;
}

export default function FilterControl({
  options,
  active,
  onChange,
}: {
  options: FilterOption[];
  active: string | null;
  onChange: (key: string | null) => void;
}) {
  return (
    <div className="inline-flex bg-syn-surface rounded-full p-1 ring-1 ring-syn-border">
      {options.map((opt) => (
        <button
          key={opt.key ?? 'all'}
          onClick={() => onChange(opt.key)}
          className={`text-xs font-semibold px-4 py-1.5 rounded-full transition-all duration-200 ${
            active === opt.key
              ? 'bg-syn-accent/15 text-syn-accent shadow-sm'
              : 'text-syn-muted hover:text-syn-text-secondary'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
