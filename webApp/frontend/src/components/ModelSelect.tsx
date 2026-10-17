import { useId } from "react";

export type ModelOption = {
  value: string;
  label: string;
};

type ModelSelectProps = {
  label: string;
  value: string;
  options: readonly ModelOption[];
  disabled?: boolean;
  onChange: (value: string) => void;
};

export function ModelSelect({
  label,
  value,
  options,
  disabled = false,
  onChange,
}: ModelSelectProps) {
  const id = useId();

  return (
    <div className="model-select">
      <label className="model-select__label" htmlFor={id}>
        {label}
      </label>
      <select
        id={id}
        className="model-select__control"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="" disabled>
          Select {label.toLowerCase()}
        </option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
