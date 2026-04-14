import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { MembershipResponse, MembershipDetails } from '../models/user.model';

export interface MembershipCreate {
  user_id: number;
  role_id: number;
  entity_id?: number;
}

@Injectable({
  providedIn: 'root'
})
export class MembershipsService {
  private apiUrl = `${environment.apiUrl}/memberships`;

  constructor(private http: HttpClient) { }

  createMembership(membership: MembershipCreate): Observable<MembershipResponse> {
    return this.http.post<MembershipResponse>(this.apiUrl, membership);
  }

  getMemberships(): Observable<MembershipDetails[]> {
    return this.http.get<MembershipDetails[]>(this.apiUrl);
  }

  getMembership(membershipId: number): Observable<MembershipDetails> {
    return this.http.get<MembershipDetails>(`${this.apiUrl}/${membershipId}`);
  }

  updateMembership(membershipId: number, membership: Partial<MembershipCreate>): Observable<MembershipResponse> {
    return this.http.put<MembershipResponse>(`${this.apiUrl}/${membershipId}`, membership);
  }

  deleteMembership(membershipId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${membershipId}`);
  }
}
