import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  ActivityResponse,
  ActivityCreate,
  ActivityUpdate,
  ActivityRegistrationOut,
  ActivityRegistrationWithUser,
  EntityResponse
} from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class ActivitiesService {
  private apiUrl = `${environment.apiUrl}/activities`;

  constructor(private http: HttpClient) {}

  // Get entities where user has permission to create activities
  getEntitiesWithCreatePermission(): Observable<EntityResponse[]> {
    return this.http.get<EntityResponse[]>(`${this.apiUrl}/entities-with-permissions`);
  }

  // Activity CRUD operations
  getActivities(): Observable<ActivityResponse[]> {
    return this.http.get<ActivityResponse[]>(this.apiUrl);
  }

  getActivity(id: number): Observable<ActivityResponse> {
    return this.http.get<ActivityResponse>(`${this.apiUrl}/${id}`);
  }

  createActivity(activity: ActivityCreate): Observable<ActivityResponse> {
    return this.http.post<ActivityResponse>(this.apiUrl, activity);
  }

  updateActivity(id: number, activity: ActivityUpdate): Observable<ActivityResponse> {
    return this.http.put<ActivityResponse>(`${this.apiUrl}/${id}`, activity);
  }

  deleteActivity(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}`);
  }

  // Image upload
  uploadActivityImage(activityId: number, file: File): Observable<{ image_url: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<{ image_url: string }>(
      `${this.apiUrl}/${activityId}/upload-image`,
      formData
    );
  }

  // Registration operations
  registerToActivity(activityId: number): Observable<ActivityRegistrationOut> {
    return this.http.post<ActivityRegistrationOut>(
      `${this.apiUrl}/${activityId}/register`,
      {}
    );
  }

  getMyRegistration(activityId: number): Observable<ActivityRegistrationOut | null> {
    return this.http.get<ActivityRegistrationOut | null>(
      `${this.apiUrl}/${activityId}/my-registration`
    );
  }

  getRegistrations(activityId: number): Observable<ActivityRegistrationOut[]> {
    return this.http.get<ActivityRegistrationOut[]>(
      `${this.apiUrl}/${activityId}/registrations`
    );
  }

  acceptRegistration(activityId: number, userId: number): Observable<ActivityRegistrationOut> {
    return this.http.post<ActivityRegistrationOut>(
      `${this.apiUrl}/${activityId}/registrations/${userId}/accept`,
      {}
    );
  }

  rejectRegistration(activityId: number, userId: number): Observable<ActivityRegistrationOut> {
    return this.http.post<ActivityRegistrationOut>(
      `${this.apiUrl}/${activityId}/registrations/${userId}/reject`,
      {}
    );
  }
}
