import { Icon } from '../lib/icons';

type BulkBarProps = {
  count: number;
  onApprove?: () => void;
  onPush?: () => void;
  onClear?: () => void;
};

export function AgBulkBar({ count, onApprove, onPush, onClear }: BulkBarProps) {
  return (
    <div className="ag-bulkbar">
      <span className="ag-bulkbar-count">{count} selected</span>
      <button type="button" onClick={onApprove}>
        <Icon.Check width={12} height={12} /> Approve
      </button>
      <button type="button">
        <Icon.ArrowUp width={12} height={12} /> Set priority
      </button>
      <button type="button" data-primary onClick={onPush}>
        <Icon.Push width={12} height={12} /> Push to DevOps
      </button>
      <button type="button">
        <Icon.Split width={12} height={12} /> Split
      </button>
      <button type="button">
        <Icon.Trash width={12} height={12} />
      </button>
      <button type="button" className="ag-bulkbar-x" onClick={onClear} title="Clear selection">
        <Icon.X width={12} height={12} />
      </button>
    </div>
  );
}
