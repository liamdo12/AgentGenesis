import type { Tweaks } from '../lib/use-tweaks';

type SetTweak = <K extends keyof Tweaks>(key: K, value: Tweaks[K]) => void;

export function TweaksPanel({ t, setTweak }: { t: Tweaks; setTweak: SetTweak }) {
  return (
    <div className="tweaks-panel" role="region" aria-label="Tweaks">
      <header className="tweaks-panel-head">Tweaks</header>

      <div className="tweaks-section">Appearance</div>
      <TweakRadio
        label="Theme"
        value={t.theme}
        options={['light', 'dark']}
        onChange={(v) => setTweak('theme', v)}
      />
      <TweakRadio
        label="Density"
        value={t.density}
        options={['compact', 'comfortable']}
        onChange={(v) => setTweak('density', v)}
      />

      <div className="tweaks-section">Story cards</div>
      <TweakRadio
        label="Style"
        value={t.cardStyle}
        options={['bordered', 'flat', 'hairline']}
        onChange={(v) => setTweak('cardStyle', v)}
      />
    </div>
  );
}

function TweakRadio<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: T[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="tweaks-row">
      <label>{label}</label>
      <div className="tweaks-radio">
        {options.map((opt) => (
          <button
            key={opt}
            type="button"
            data-active={opt === value ? '' : undefined}
            onClick={() => onChange(opt)}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}
