import { useId } from "react";

import { ClearIcon } from "./icons";

type TextFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
};

export function TextField({ label, value, onChange }: TextFieldProps) {
  const id = useId();
  return (
    <div className="text-field">
      <input
        id={id}
        className="text-field__input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      <label className="text-field__label" htmlFor={id}>
        {label}
      </label>
      {value && (
        <button
          type="button"
          className="text-field__clear"
          aria-label={`Clear ${label}`}
          onClick={() => onChange("")}
        >
          <ClearIcon width={20} height={20} />
        </button>
      )}
    </div>
  );
}
