import { Router } from '@angular/router';

interface NotificationTarget {
  event_type?: string;
  resource_type?: string;
  resource_id?: string | number | null;
}

export function openNotification(router: Router, target?: NotificationTarget): void {
  if (!target) return;
  const { resource_type: type, resource_id, event_type } = target;
  if (type === 'memberships') { void router.navigate(['/dashboard']); return; }
  const id = String(resource_id ?? '');
  if (!/^[1-9]\d*$/.test(id)) return;
  const event = (event_type ?? '').toLowerCase().replace(/^eventtype\./, '');
  if (type === 'membership_requests') {
    const decision = event === 'membership_request_accepted' || event === 'membership_request_rejected';
    void router.navigate([decision ? '/pending' : '/membership-requests'], { queryParams: { request: id } });
    return;
  }
  if (type === 'chat') {
    void router.navigate(['/chat'], { queryParams: { conversation: id } });
    return;
  }
  if (type === 'fee_assignments') {
    void router.navigate([event === 'fee_proof_submitted' ? '/fees' : '/fees/mine']);
    return;
  }
  const routes: Record<string, string> = {
    magazines: '/magazines', activities: '/activities', communications: '/communications', resources: '/resources'
  };
  if (type && Object.prototype.hasOwnProperty.call(routes, type)) void router.navigate([routes[type], id]);
}
