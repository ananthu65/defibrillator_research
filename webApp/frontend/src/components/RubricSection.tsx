import { CheckIcon } from "./icons";

export type RubricItem = {
  id: string;
  label: string;
  checked: boolean;
  /** Flagged by the auto review as missed; shown as an error while unchecked. */
  flagged?: boolean;
};

type RubricSectionProps = {
  title: string;
  items: RubricItem[];
  onToggle: (id: string) => void;
};

export function RubricSection({ title, items, onToggle }: RubricSectionProps) {
  return (
    <section className="rubric">
      <h2 className="section-title">{title}</h2>
      <ul className="rubric__list">
        {items.map((item) => {
          const error = item.flagged && !item.checked;
          return (
            <li key={item.id}>
              <label className="rubric__row">
                <span className="checkbox">
                  <input
                    type="checkbox"
                    className="checkbox__input"
                    checked={item.checked}
                    data-error={error || undefined}
                    onChange={() => onToggle(item.id)}
                  />
                  <span className="checkbox__box">
                    <CheckIcon width={16} height={16} />
                  </span>
                </span>
                <span className="rubric__label">{item.label}</span>
              </label>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
