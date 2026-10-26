import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, forkJoin } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { UserResponse, UserCreate, UserUpdate, UserDetails, PaginatedUsers, ConsentStatus } from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class UsersService {
  private apiUrl = `${environment.apiUrl}/users`;

  constructor(private http: HttpClient) { }

  private listParams(skip: number, limit: number, search?: string): HttpParams {
    let params = new HttpParams()
      .set('skip', skip.toString())
      .set('limit', limit.toString());
    // The backend rejects an empty search with 422 (min_length=1), so it is
    // omitted rather than sent blank.
    if (search && search.trim()) {
      params = params.set('search', search.trim());
    }
    return params;
  }

  /**
   * Mint a fresh sign-in link to hand over in person.
   *
   * For members the welcome email cannot reach: registered with a phone and no
   * address, or the message never arrived. Only works for accounts that have
   * never set a password of their own.
   */
  issueActivationLink(
    userId: number
  ): Observable<{ url: string; expires_in_hours: number }> {
    return this.http.post<{ url: string; expires_in_hours: number }>(
      `${this.apiUrl}/${userId}/activation-link`,
      {}
    );
  }

  /** Associations where the caller may create users. */
  getCreatableEntities(): Observable<{ id: number; name: string }[]> {
    return this.http.get<{ id: number; name: string }[]>(
      `${this.apiUrl}/creatable-entities`
    );
  }

  getUsers(skip = 0, limit = 50, search?: string): Observable<PaginatedUsers> {
    return this.http.get<PaginatedUsers>(this.apiUrl, {
      params: this.listParams(skip, limit, search)
    });
  }

  getManagedUsers(skip = 0, limit = 50, search?: string): Observable<PaginatedUsers> {
    return this.http.get<PaginatedUsers>(`${this.apiUrl}/managed`, {
      params: this.listParams(skip, limit, search)
    });
  }

  getConsentStatus(): Observable<ConsentStatus> {
    return this.http.get<ConsentStatus>(`${this.apiUrl}/me/consent`);
  }

  acceptConsent(version: string): Observable<ConsentStatus> {
    return this.http.post<ConsentStatus>(`${this.apiUrl}/me/consent`, { version });
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

  getMyProfile(): Observable<UserDetails> {
    return this.http.get<UserDetails>(`${this.apiUrl}/me`);
  }

  updateMyProfile(user: UserUpdate): Observable<UserResponse> {
    return this.http.put<UserResponse>(`${this.apiUrl}/me`, user);
  }

  uploadMyPhoto(file: File): Observable<UserResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<UserResponse>(`${this.apiUrl}/me/photo`, formData);
  }

  uploadUserPhoto(userId: number, file: File): Observable<UserResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<UserResponse>(`${this.apiUrl}/${userId}/photo`, formData);
  }

  /**
   * Borra la cuenta del usuario autenticado.
   *
   * La contraseña se vuelve a pedir aunque ya haya sesión: la operación es
   * irreversible y una sesión olvidada en un móvil compartido no debería
   * bastar para borrar una cuenta.
   */
  deleteMyAccount(password: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.apiUrl}/me`, {
      body: { password }
    });
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
