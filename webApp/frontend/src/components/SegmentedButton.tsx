import { CheckIcon } from "./icons";

type SegmentedButtonProps<T extends string> = {
  options: readonly { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  label: string;
};

export function SegmentedButton<T extends string>({
  options,
  value,
  onChange,
  label,
}: SegmentedButtonProps<T>) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            className="segmented__segment"
            aria-pressed={selected}
            onClick={() => onChange(option.value)}
          >
            {selected && <CheckIcon width={18} height={18} />}
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
