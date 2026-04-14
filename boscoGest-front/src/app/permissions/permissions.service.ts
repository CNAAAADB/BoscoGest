import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { PermissionResponse } from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class PermissionsService {
  private apiUrl = `${environment.apiUrl}/permissions`;

  constructor(private http: HttpClient) {}

  getPermissions(skip: number = 0, limit: number = 100): Observable<PermissionResponse[]> {
    return this.http.get<PermissionResponse[]>(this.apiUrl, {
      params: { skip: skip.toString(), limit: limit.toString() }
    });
  }

  assignPermissionToRole(permissionId: number, roleId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/${permissionId}/assign-to-role/${roleId}`, {});
  }
}
