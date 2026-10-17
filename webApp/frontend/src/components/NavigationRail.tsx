import { EditIcon, MenuIcon, StarIcon } from "./icons";

export type NavDestination = { id: string; label: string };

type NavigationRailProps = {
  destinations: NavDestination[];
  activeId: string;
  onSelect: (id: string) => void;
};

export function NavigationRail({
  destinations,
  activeId,
  onSelect,
}: NavigationRailProps) {
  return (
    <nav className="nav-rail" aria-label="Primary">
      <div className="nav-rail__header">
        <button type="button" className="icon-button" aria-label="Menu">
          <MenuIcon />
        </button>
        <button type="button" className="fab" aria-label="New review">
          <EditIcon />
        </button>
      </div>
      <ul className="nav-rail__segments">
        {destinations.map(({ id, label }) => {
          const selected = id === activeId;
          return (
            <li key={id}>
              <button
                type="button"
                className="nav-item"
                aria-current={selected ? "page" : undefined}
                onClick={() => onSelect(id)}
              >
                <span className="nav-item__indicator">
                  <StarIcon width={20} height={20} />
                </span>
                <span className="nav-item__label">{label}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
