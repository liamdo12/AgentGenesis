import { useCallback, type MouseEvent } from 'react';
import { createPortal } from 'react-dom';
import { useAppDispatch, useAppState } from '../state/app-state-context';
import { EditStoryModal } from './edit-story-modal';
import { DevOpsPushModal } from './devops-push-modal';
import { useBodyScrollLock } from './use-body-scroll-lock';
import { useEscape } from './use-escape';

export function ModalHost() {
  const { modal } = useAppState();
  const dispatch = useAppDispatch();

  const close = useCallback(() => dispatch({ type: 'CLOSE_MODAL' }), [dispatch]);

  if (!modal) return null;
  return <Mounted modal={modal} close={close} />;
}

type MountedProps = {
  modal: NonNullable<ReturnType<typeof useAppState>['modal']>;
  close: () => void;
};

function Mounted({ modal, close }: MountedProps) {
  useEscape(close);
  useBodyScrollLock();
  const { stories, tweaks } = useAppState();

  // Backdrop click closes; clicks inside the modal don't bubble.
  const onBackdropMouseDown = (e: MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) close();
  };

  const content =
    modal.kind === 'edit' ? (() => {
      const story = stories.find((s) => s.id === modal.storyId);
      if (!story) return null;
      return <EditStoryModal story={story} onClose={close} />;
    })() : <DevOpsPushModal onClose={close} />;

  // We portal to <body>, but the modal's CSS relies on theme tokens
  // (--ag-surface, --ag-border, --ag-shadow-lg, …) that are scoped to
  // .ag-app[data-theme]. Wrap the portal content in a themed .ag-app
  // container so those custom properties resolve.
  return createPortal(
    <div
      className="ag-app ag-modal-portal"
      data-theme={tweaks.theme}
      data-density={tweaks.density}
    >
      <div className="ag-modal-backdrop" onMouseDown={onBackdropMouseDown}>
        {content}
      </div>
    </div>,
    document.body,
  );
}
