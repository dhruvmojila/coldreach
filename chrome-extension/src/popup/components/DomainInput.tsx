interface Props {
  value: string;
  onChange: (v: string) => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  disabled: boolean;
}

export function DomainInput({ value, onChange, onKeyDown, disabled }: Props) {
  return (
    <div>
      <label className="block text-xs text-gray-400 mb-1">Domain or company</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled}
        placeholder="stripe.com or company name"
        className="
          w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700
          text-white placeholder-gray-500 text-sm outline-none
          focus:border-brand focus:ring-1 focus:ring-brand
          disabled:opacity-50 disabled:cursor-not-allowed
          transition-colors
        "
        autoFocus
      />
    </div>
  );
}
