import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  FeeResponse,
  FeeCreate,
  FeeConfigResponse,
  FeeVersionCreate,
  FeeAssignmentResponse,
  FeeAssignmentGenerateRequest,
  FeeAssignmentStatusUpdate,
  FeeGenerateResult,
  FeeStatus,
  MemberPreview,
  EntityResponse,
  FeeMaintenanceRun,
  FeeSubscriptionResponse,
  FeeSubscribeRequest
} from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class FeesService {
  private apiUrl = `${environment.apiUrl}/fees`;

  constructor(private http: HttpClient) {}

  // ── Entities selector ──────────────────────────────────────────────────────

  getFeeEntities(): Observable<EntityResponse[]> {
    return this.http.get<EntityResponse[]>(`${this.apiUrl}/entities`);
  }

  // ── Fees ────────────────────────────────────────────────────────────────────

  listFees(entityId: number): Observable<FeeResponse[]> {
    const params = new HttpParams().set('entity_id', entityId.toString());
    return this.http.get<FeeResponse[]>(this.apiUrl, { params });
  }

  createFee(payload: FeeCreate): Observable<FeeResponse[]> {
    return this.http.post<FeeResponse[]>(this.apiUrl, payload);
  }

  getFeeHistory(feeId: number): Observable<FeeConfigResponse[]> {
    return this.http.get<FeeConfigResponse[]>(`${this.apiUrl}/${feeId}/history`);
  }

  addFeeVersion(feeId: number, payload: FeeVersionCreate): Observable<FeeConfigResponse> {
    return this.http.post<FeeConfigResponse>(`${this.apiUrl}/${feeId}/versions`, payload);
  }

  deleteFee(feeId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${feeId}`);
  }

  // ── Assignments ───────────────────────────────────────────────────────────

  getMembersPreview(feeId: number, referenceDate?: string): Observable<MemberPreview[]> {
    let params = new HttpParams().set('fee_id', feeId.toString());
    if (referenceDate) params = params.set('reference_date', referenceDate);
    return this.http.get<MemberPreview[]>(`${this.apiUrl}/members-preview`, { params });
  }

  getMyAssignments(): Observable<FeeAssignmentResponse[]> {
    return this.http.get<FeeAssignmentResponse[]>(`${this.apiUrl}/assignments/mine`);
  }

  listAssignments(
    entityId: number,
    filters?: { feeId?: number; period?: string; status?: FeeStatus }
  ): Observable<FeeAssignmentResponse[]> {
    let params = new HttpParams().set('entity_id', entityId.toString());
    if (filters?.feeId) params = params.set('fee_id', filters.feeId.toString());
    if (filters?.period) params = params.set('period', filters.period);
    if (filters?.status) params = params.set('status', filters.status);
    return this.http.get<FeeAssignmentResponse[]>(`${this.apiUrl}/assignments`, { params });
  }

  generateAssignments(body: FeeAssignmentGenerateRequest): Observable<FeeGenerateResult> {
    return this.http.post<FeeGenerateResult>(`${this.apiUrl}/assignments/generate`, body);
  }

  updateAssignmentStatus(
    assignmentId: number,
    body: FeeAssignmentStatusUpdate
  ): Observable<FeeAssignmentResponse> {
    return this.http.patch<FeeAssignmentResponse>(
      `${this.apiUrl}/assignments/${assignmentId}/status`,
      body
    );
  }

  // ── Maintenance / monitoring ───────────────────────────────────────────────

  runMaintenance(): Observable<FeeMaintenanceRun> {
    return this.http.post<FeeMaintenanceRun>(`${this.apiUrl}/maintenance/run`, {});
  }

  getMaintenanceRuns(): Observable<FeeMaintenanceRun[]> {
    return this.http.get<FeeMaintenanceRun[]>(`${this.apiUrl}/maintenance/runs`);
  }

  // ── Enrolments ────────────────────────────────────────────────────────────
  // Who owes a fee. Generation and the nightly renewal both read this, so a
  // member is charged because they are enrolled, not because they happened to
  // be charged last period.

  listSubscriptions(feeId: number): Observable<FeeSubscriptionResponse[]> {
    return this.http.get<FeeSubscriptionResponse[]>(`${this.apiUrl}/${feeId}/subscriptions`);
  }

  subscribe(feeId: number, body: FeeSubscribeRequest): Observable<FeeSubscriptionResponse[]> {
    return this.http.post<FeeSubscriptionResponse[]>(
      `${this.apiUrl}/${feeId}/subscriptions`,
      body
    );
  }

  unsubscribe(feeId: number, userId: number, endsOn?: string): Observable<void> {
    return this.http.request<void>(
      'DELETE',
      `${this.apiUrl}/${feeId}/subscriptions/${userId}`,
      { body: { ends_on: endsOn ?? null } }
    );
  }

  setExemption(
    feeId: number,
    userId: number,
    exempt: boolean,
    reason?: string | null
  ): Observable<FeeSubscriptionResponse> {
    return this.http.patch<FeeSubscriptionResponse>(
      `${this.apiUrl}/${feeId}/subscriptions/${userId}/exemption`,
      { exempt, reason: reason ?? null }
    );
  }

  // ── Proof of payment ──────────────────────────────────────────────────────

  submitProof(
    assignmentId: number,
    file: File,
    reference?: string
  ): Observable<FeeAssignmentResponse> {
    const form = new FormData();
    form.append('file', file);
    if (reference) {
      form.append('reference', reference);
    }
    return this.http.post<FeeAssignmentResponse>(
      `${this.apiUrl}/assignments/${assignmentId}/proof`,
      form
    );
  }

  /** Short-lived link to the receipt, for its author or a reviewer. */
  getProofUrl(assignmentId: number): Observable<{ url: string }> {
    return this.http.get<{ url: string }>(
      `${this.apiUrl}/assignments/${assignmentId}/proof`
    );
  }

  rejectProof(assignmentId: number, reason: string): Observable<FeeAssignmentResponse> {
    return this.http.post<FeeAssignmentResponse>(
      `${this.apiUrl}/assignments/${assignmentId}/proof/reject`,
      { reason }
    );
  }
}
