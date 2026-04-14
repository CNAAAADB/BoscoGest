import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { RoleResponse, RoleCreate, RoleUpdate, RoleDetails } from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class RolesService {
  private apiUrl = `${environment.apiUrl}/roles`;

  constructor(private http: HttpClient) {}

  getRoles(skip: number = 0, limit: number = 100): Observable<RoleResponse[]> {
    return this.http.get<RoleResponse[]>(this.apiUrl, {
      params: { skip: skip.toString(), limit: limit.toString() }
    });
  }

  getRole(roleId: number): Observable<RoleDetails> {
    return this.http.get<RoleDetails>(`${this.apiUrl}/${roleId}`);
  }

  createRole(role: RoleCreate): Observable<RoleResponse> {
    return this.http.post<RoleResponse>(this.apiUrl, role);
  }

  updateRole(roleId: number, role: RoleUpdate): Observable<RoleResponse> {
    return this.http.put<RoleResponse>(`${this.apiUrl}/${roleId}`, role);
  }

  deleteRole(roleId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${roleId}`);
  }
}
