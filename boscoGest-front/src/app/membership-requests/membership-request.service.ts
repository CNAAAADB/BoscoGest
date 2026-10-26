import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  MembershipRequestResponse,
  RegisterRequest,
} from '../models/user.model';

@Injectable({ providedIn: 'root' })
export class MembershipRequestService {
  private http = inject(HttpClient);
  private apiUrl = environment.apiUrl;

  /** Public — no auth required. Creates user account + membership request. */
  register(data: RegisterRequest): Observable<MembershipRequestResponse> {
    return this.http.post<MembershipRequestResponse>(
      `${this.apiUrl}/auth/register`,
      data
    );
  }

  /** Returns the current user's own membership requests. */
  getMyRequests(): Observable<MembershipRequestResponse[]> {
    return this.http.get<MembershipRequestResponse[]>(
      `${this.apiUrl}/membership-requests/mine`
    );
  }

  /** Admin: list pending (or all) requests, optionally filtered by entity. */
  getRequests(
    entityId?: number,
    status?: string
  ): Observable<MembershipRequestResponse[]> {
    const params: Record<string, string> = {};
    if (entityId) params['entity_id'] = String(entityId);
    if (status) params['status'] = status;
    return this.http.get<MembershipRequestResponse[]>(
      `${this.apiUrl}/membership-requests`,
      { params }
    );
  }

  /** Admin: accept a request. */
  acceptRequest(requestId: number): Observable<MembershipRequestResponse> {
    return this.http.post<MembershipRequestResponse>(
      `${this.apiUrl}/membership-requests/${requestId}/accept`,
      {}
    );
  }

  /** Admin: reject a request with an optional reason. */
  rejectRequest(
    requestId: number,
    rejectionReason?: string
  ): Observable<MembershipRequestResponse> {
    return this.http.post<MembershipRequestResponse>(
      `${this.apiUrl}/membership-requests/${requestId}/reject`,
      { rejection_reason: rejectionReason ?? null }
    );
  }

  /** User: cancel own pending request. */
  cancelRequest(requestId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.apiUrl}/membership-requests/${requestId}`
    );
  }

  /** Public — get available entities for registration form. */
  getPublicEntities(): Observable<{ id: number; name: string; level: number }[]> {
    return this.http.get<{ id: number; name: string; level: number }[]>(
      `${this.apiUrl}/entities/public`
    );
  }
}
