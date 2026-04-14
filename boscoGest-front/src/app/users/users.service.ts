import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, forkJoin } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { UserResponse, UserCreate, UserUpdate, UserDetails } from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class UsersService {
  private apiUrl = `${environment.apiUrl}/users`;

  constructor(private http: HttpClient) { }

  getUsers(skip: number = 0, limit: number = 100): Observable<UserResponse[]> {
    return this.http.get<UserResponse[]>(this.apiUrl, {
      params: { skip: skip.toString(), limit: limit.toString() }
    });
  }

  getManagedUsers(skip: number = 0, limit: number = 100): Observable<UserResponse[]> {
    return this.http.get<UserResponse[]>(`${this.apiUrl}/managed`, {
      params: { skip: skip.toString(), limit: limit.toString() }
    });
  }

  getUser(userId: number): Observable<UserResponse> {
    return this.http.get<UserResponse>(`${this.apiUrl}/${userId}`);
  }

  getUserDetails(userId: number): Observable<UserDetails> {
    return this.http.get<UserDetails>(`${this.apiUrl}/${userId}`);
  }

  createUser(user: UserCreate): Observable<UserResponse> {
    return this.http.post<UserResponse>(this.apiUrl, user);
  }

  updateUser(userId: number, user: UserUpdate): Observable<UserResponse> {
    return this.http.put<UserResponse>(`${this.apiUrl}/${userId}`, user);
  }

  deleteUser(userId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${userId}`);
  }

  searchUserByEmail(email: string): Observable<UserResponse | null> {
    return this.http.get<UserResponse>(`${this.apiUrl}/search/email/${encodeURIComponent(email)}`);
  }

  searchUserByDni(dni: string): Observable<UserResponse | null> {
    return this.http.get<UserResponse>(`${this.apiUrl}/search/dni/${encodeURIComponent(dni)}`);
  }
}
