import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ConsentClause, ConsentClauseCreate } from '../models/user.model';

export interface ConsentPendingCount {
  current_version: string;
  pending: number;
}

/**
 * Authoring side of the GDPR clause, gated behind consent:manage.
 *
 * The clause is platform-wide, not per entity: every member of every
 * association is processed under the same terms.
 */
@Injectable({ providedIn: 'root' })
export class ConsentClausesService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/consent-clauses`;

  list(): Observable<ConsentClause[]> {
    return this.http.get<ConsentClause[]>(this.apiUrl);
  }

  pendingCount(): Observable<ConsentPendingCount> {
    return this.http.get<ConsentPendingCount>(`${this.apiUrl}/pending-count`);
  }

  create(payload: ConsentClauseCreate): Observable<ConsentClause> {
    return this.http.post<ConsentClause>(this.apiUrl, payload);
  }

  /** Only drafts can be edited; the API answers 409 for published versions. */
  updateDraft(id: number, text: string): Observable<ConsentClause> {
    return this.http.put<ConsentClause>(`${this.apiUrl}/${id}`, { text });
  }

  publish(id: number): Observable<ConsentClause> {
    return this.http.post<ConsentClause>(`${this.apiUrl}/${id}/publish`, {});
  }

  deleteDraft(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}
