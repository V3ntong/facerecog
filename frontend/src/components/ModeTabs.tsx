interface Tab {
  id: string;
  label: string;
}

interface Props {
  tabs: readonly Tab[];
  active: string;
  onSelect: (id: string) => void;
}

/**
 * Sections as a ruled line, not a pill: the active one is set in ink with a
 * printed rule under it. The wax pencil stays reserved for recognition, so
 * selection is never pink.
 */
export default function ModeTabs({ tabs, active, onSelect }: Props) {
  return (
    <div role="tablist" aria-label="How to add a subject" className="flex gap-6 border-b border-rule">
      {tabs.map((tab) => {
        const selected = tab.id === active;
        return (
          <button
            key={tab.id}
            id={`tab-${tab.id}`}
            role="tab"
            type="button"
            aria-selected={selected}
            aria-controls={`panel-${tab.id}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onSelect(tab.id)}
            className={`type-ui relative -mb-px cursor-pointer pb-2 ${
              selected ? "text-ink" : "text-slate hover:text-ink"
            }`}
          >
            {tab.label}
            {selected && (
              <span aria-hidden="true" className="absolute inset-x-0 bottom-0 h-[2px] bg-ink" />
            )}
          </button>
        );
      })}
    </div>
  );
}
