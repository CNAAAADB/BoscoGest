import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  CommunicationResponse,
  CommunicationCreate,
  CommunicationUpdate,
  CommunicationWithCommentsResponse,
  CommunicationStatus,
  StatusTransitionRequest,
  CommentResponse,
  CommentCreate,
  CommentUpdate,
  EntityResponse
} from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class CommunicationsService {
  private newsApiUrl = `${environment.apiUrl}/communications`;
  private commentsApiUrl = `${environment.apiUrl}/comments`;

  constructor(private http: HttpClient) {}

  getEntitiesWithCreatePermission(): Observable<EntityResponse[]> {
    return this.http.get<EntityResponse[]>(`${this.newsApiUrl}/entities-with-permissions`);
  }

  // News CRUD operations
  getNewsList(skip: number = 0, limit: number = 10, status?: CommunicationStatus): Observable<CommunicationResponse[]> {
    let url = `${this.newsApiUrl}?skip=${skip}&limit=${limit}`;
    if (status) {
      url += `&status=${status}`;
    }
    return this.http.get<CommunicationResponse[]>(url);
  }

  getNewsCount(status?: CommunicationStatus): Observable<{ total: number }> {
    let url = `${this.newsApiUrl}/count`;
    if (status) {
      url += `?status=${status}`;
    }
    return this.http.get<{ total: number }>(url);
  }

  transitionStatus(id: number, targetStatus: CommunicationStatus): Observable<CommunicationResponse> {
    const body: StatusTransitionRequest = { target_status: targetStatus };
    return this.http.patch<CommunicationResponse>(`${this.newsApiUrl}/${id}/status`, body);
  }

  getNews(id: number): Observable<CommunicationWithCommentsResponse> {
    return this.http.get<CommunicationWithCommentsResponse>(`${this.newsApiUrl}/${id}`);
  }

  createNews(news: CommunicationCreate): Observable<CommunicationResponse> {
    return this.http.post<CommunicationResponse>(this.newsApiUrl, news);
  }

  updateNews(id: number, news: CommunicationUpdate): Observable<CommunicationResponse> {
    return this.http.put<CommunicationResponse>(`${this.newsApiUrl}/${id}`, news);
  }

  deleteNews(id: number): Observable<any> {
    return this.http.delete(`${this.newsApiUrl}/${id}`);
  }

  // Image upload
  uploadNewsImage(communicationId: number, file: File): Observable<{ image_url: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<{ image_url: string }>(
      `${this.newsApiUrl}/${communicationId}/upload-image`,
      formData
    );
  }

  // Comment operations
  getComments(communicationId: number): Observable<CommentResponse[]> {
    return this.http.get<CommentResponse[]>(`${this.commentsApiUrl}/communications/${communicationId}/comments`);
  }

  createComment(communicationId: number, comment: CommentCreate): Observable<CommentResponse> {
    return this.http.post<CommentResponse>(`${this.commentsApiUrl}/communications/${communicationId}/comments`, comment);
  }

  updateComment(commentId: number, comment: CommentUpdate): Observable<CommentResponse> {
    return this.http.put<CommentResponse>(`${this.commentsApiUrl}/comments/${commentId}`, comment);
  }

  deleteComment(commentId: number): Observable<any> {
    return this.http.delete(`${this.commentsApiUrl}/comments/${commentId}`);
  }
}
