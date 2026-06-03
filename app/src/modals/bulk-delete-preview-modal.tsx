/**
 * Confirms a bulk-delete revision Claude proposed.
 *
 * Server only commits on Accept (POST .../preview/{id}/accept). Reject just
 * discards the in-memory preview locally — Claude can be asked again.
 */

import type { BulkPreview } from '../hooks/use-chat';

type Props = {
  preview: BulkPreview;
  onAccept: () => void;
  onReject: () => void;
};

export function BulkDeletePreviewModal({ preview, onAccept, onReject }: Props) {
  return (
    <div className="ag-modal-backdrop" onMouseDown={(e) => {
      if (e.target === e.currentTarget) onReject();
    }}>
      <div className="ag-modal" role="dialog" aria-labelledby="bulk-delete-title">
        <div className="ag-modal-head">
          <h2 id="bulk-delete-title" className="ag-modal-title">
            Confirm bulk delete
          </h2>
        </div>
        <div className="ag-modal-body">
          <p>
            Claude wants to delete <strong>{preview.removedIds.length} stories</strong>:
          </p>
          <ul style={{ paddingLeft: 20, lineHeight: 1.6 }}>
            {preview.removedIds.map((id) => (
              <li key={id}><code>{id}</code></li>
            ))}
          </ul>
          <p style={{ fontSize: 12, color: 'var(--ag-text-muted)' }}>
            Reject to keep them. Accept to commit a new revision with these
            stories removed. You can always restore the previous revision
            via chat.
          </p>
        </div>
        <div className="ag-modal-foot">
          <button type="button" className="ag-btn" onClick={onReject}>
            Reject
          </button>
          <button
            type="button"
            className="ag-btn"
            data-variant="danger"
            onClick={onAccept}
          >
            Accept &amp; delete
          </button>
        </div>
      </div>
    </div>
  );
}
