import toast from 'react-hot-toast';
import { Check, Undo2, X } from 'lucide-react';
import { post, useApi } from '../../lib/useApi';
import { Badge, Button, Card, CardBody, CardHeader, ErrorBox, KeyValues, Loading, PageHeader } from '../../ui';
import { HistoryTable } from './parts';

/* Live registry: every version, who approved it, and the controls a health officer uses. */
export default function ModelHistory() {
  const status = useApi('/maintenance/live/status');
  const history = useApi('/maintenance/live/history');
  const s = status.data;

  const act = async (path, label, params) => {
    try {
      await post(path, undefined, params);
      toast.success(label);
    } catch (e) {
      toast.error(e.message);
    }
    status.reload();
    history.reload();
  };

  return (
    <div className="animate-fade-in space-y-5">
      <PageHeader
        component="c3"
        title="Versions & approvals"
        subtitle="C3 never changes the live model directly: candidates are verified, wait for approval, and can always be rolled back."
        actions={<Badge tone="success">Live model · saved across restarts</Badge>}
      />
      {status.error && <ErrorBox error={status.error} />}
      <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <div className="space-y-5">
          <Card>
            <CardHeader title="Active model" />
            <CardBody>
              {s ? (
                <KeyValues rows={[
                  ['Version', s.active_model.version],
                  ['Created by', s.active_model.action],
                  ['Built from', s.active_model.parent || '—'],
                  ['Trained', s.active_model.trained_at?.slice(0, 16).replace('T', ' ')],
                  ['Decision threshold', s.active_model.decision_threshold],
                ]} />
              ) : <Loading />}
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Approval" subtitle={s?.pending_approval ? `${s.pending_approval} passed verification and is waiting` : 'Nothing is waiting for approval'} />
            <CardBody className="flex flex-wrap gap-2">
              <Button variant="c3" disabled={!s?.pending_approval} onClick={() => act('/maintenance/live/approve', 'Approved and deployed', { approver: 'MOH officer' })}>
                <Check size={15} /> Approve and deploy
              </Button>
              <Button variant="outline" disabled={!s?.pending_approval} onClick={() => act('/maintenance/live/reject-pending', 'Candidate rejected')}>
                <X size={15} /> Reject
              </Button>
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Roll back" subtitle="Restore the previous live version immediately" />
            <CardBody>
              <Button variant="danger" onClick={() => window.confirm('Roll back to the previous model version?') && act('/maintenance/live/rollback', 'Rolled back')}>
                <Undo2 size={15} /> Roll back
              </Button>
            </CardBody>
          </Card>
        </div>
        <Card>
          <CardHeader title="Version history" subtitle="Newest first" />
          <CardBody>{history.data ? <HistoryTable rows={history.data} /> : <Loading />}</CardBody>
        </Card>
      </div>
    </div>
  );
}
