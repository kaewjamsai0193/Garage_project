import Icon from "./Icon";

// ช่องค้นหา (q/setQ) + แท็บกรอง (filter/setFilter) ถ้าส่ง filters มา
export default function SearchBar({ q, setQ, placeholder, filters, filter, setFilter }) {
  return (
    <div className="space-y-2">
      <label className="relative block">
        <span className="sr-only">{placeholder}</span>
        <Icon
          name="search"
          size={20}
          className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted"
        />
        <input
          type="search"
          className="input pl-10"
          placeholder={placeholder}
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </label>
      {filters && (
        <div role="tablist" aria-label="กรอง" className="tabs -mx-4 px-4 md:mx-0 md:px-0">
          {filters.map(([key, label]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={filter === key}
              onClick={() => setFilter(key)}
              className="tab"
            >
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
