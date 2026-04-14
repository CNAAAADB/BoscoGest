import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  ResourceResponse,
  ResourceDetails,
  ResourceCreateLink,
  ResourceCreateFile,
  ResourceUpdate,
  ResourceCategoryResponse,
  ResourceCategoryCreate,
  ResourceCategoryUpdate,
  ResourceType,
} from '../models/user.model';
import { downloadBlob } from '../utils/file-download.util';
import { fetchBlobNative } from '../utils/native-http.util';

@Injectable({
  providedIn: 'root'
})
export class ResourcesService {
  private apiUrl = `${environment.apiUrl}/resources`;
  private categoriesUrl = `${environment.apiUrl}/resource-categories`;

  constructor(private http: HttpClient) {}

  // --- Resources ---

  getResources(filters?: {
    entity_id?: number;
    category_id?: number;
    type?: ResourceType;
    tags?: string;
    search?: string;
  }): Observable<ResourceDetails[]> {
    let params = new HttpParams();
    if (filters) {
      if (filters.entity_id) params = params.set('entity_id', filters.entity_id.toString());
      if (filters.category_id) params = params.set('category_id', filters.category_id.toString());
      if (filters.type) params = params.set('type', filters.type);
      if (filters.tags) params = params.set('tags', filters.tags);
      if (filters.search) params = params.set('search', filters.search);
    }
    return this.http.get<ResourceDetails[]>(this.apiUrl, { params });
  }

  getResource(id: number): Observable<ResourceDetails> {
    return this.http.get<ResourceDetails>(`${this.apiUrl}/${id}`);
  }

  createResourceLink(resource: ResourceCreateLink): Observable<ResourceResponse> {
    return this.http.post<ResourceResponse>(`${this.apiUrl}/link`, resource);
  }

  createResourceFile(resource: ResourceCreateFile): Observable<ResourceResponse> {
    const formData = new FormData();
    formData.append('title', resource.title);
    formData.append('resource_type', resource.resource_type);
    formData.append('entity_id', resource.entity_id.toString());
    formData.append('file', resource.file);

    if (resource.description) {
      formData.append('description', resource.description);
    }
    if (resource.tags) {
      formData.append('tags', resource.tags);
    }
    if (resource.category_id) {
      formData.append('category_id', resource.category_id.toString());
    }

    return this.http.post<ResourceResponse>(this.apiUrl, formData);
  }

  updateResource(id: number, resource: ResourceUpdate): Observable<ResourceResponse> {
    return this.http.put<ResourceResponse>(`${this.apiUrl}/${id}`, resource);
  }

  deleteResource(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  getResourceFileUrl(id: number): string {
    return `${this.apiUrl}/${id}/file`;
  }

  getResourceFileBlob(id: number): Observable<Blob> {
    return fetchBlobNative(
      `${this.apiUrl}/${id}/file`,
      () => this.http.get(`${this.apiUrl}/${id}/file`, { responseType: 'blob' })
    );
  }

  downloadResource(id: number, filename: string): void {
    this.getResourceFileBlob(id).subscribe({
      next: (blob) => {
        downloadBlob(blob, filename);
      },
      error: (error) => {
        console.error('Error downloading resource:', error);
      }
    });
  }

  // --- Categories ---

  getCategories(entityId: number): Observable<ResourceCategoryResponse[]> {
    const params = new HttpParams().set('entity_id', entityId.toString());
    return this.http.get<ResourceCategoryResponse[]>(this.categoriesUrl, { params });
  }

  createCategory(category: ResourceCategoryCreate): Observable<ResourceCategoryResponse> {
    return this.http.post<ResourceCategoryResponse>(this.categoriesUrl, category);
  }

  updateCategory(id: number, category: ResourceCategoryUpdate): Observable<ResourceCategoryResponse> {
    return this.http.put<ResourceCategoryResponse>(`${this.categoriesUrl}/${id}`, category);
  }

  deleteCategory(id: number): Observable<void> {
    return this.http.delete<void>(`${this.categoriesUrl}/${id}`);
  }
}
