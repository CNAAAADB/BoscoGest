import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  MagazineResponse,
  MagazineDetails,
  MagazineCreate,
  MagazineUpdate
} from '../models/user.model';
import { downloadBlob } from '../utils/file-download.util';
import { fetchBlobNative } from '../utils/native-http.util';

export interface ArchiveIssue {
  id: number;
  publication: string;
  publication_year: number;
  first_page: number;
}

export interface ArchiveCatalog {
  issues: ArchiveIssue[];
  has_more: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class MagazinesService {
  private apiUrl = `${environment.apiUrl}/magazines`;

  constructor(private http: HttpClient) {}

  /**
   * Get all magazines (filtered by user's accessible entities)
   */
  getArchiveCatalog(page: number): Observable<ArchiveCatalog> {
    return this.http.get<ArchiveCatalog>(`${this.apiUrl}/archive/catalog`, { params: { page } });
  }

  getMagazines(): Observable<MagazineDetails[]> {
    return this.http.get<MagazineDetails[]>(this.apiUrl);
  }

  /**
   * Get magazine details by ID
   */
  getMagazineDetails(id: number): Observable<MagazineDetails> {
    return this.http.get<MagazineDetails>(`${this.apiUrl}/${id}`);
  }

  /**
   * Get magazine PDF file URL
   */
  getMagazineFileUrl(id: number): string {
    return `${this.apiUrl}/${id}/file`;
  }

  /**
   * Get magazine PDF file as Blob (with authentication)
   */
  getMagazineFileBlob(id: number): Observable<Blob> {
    return fetchBlobNative(
      `${this.apiUrl}/${id}/file`,
      () => this.http.get(`${this.apiUrl}/${id}/file`, { responseType: 'blob' })
    );
  }

  /**
   * Create a new magazine
   */
  createMagazine(magazine: MagazineCreate): Observable<MagazineResponse> {
    const formData = new FormData();
    formData.append('title', magazine.title);
    formData.append('entity_id', magazine.entity_id.toString());

    if (magazine.collection) {
      formData.append('collection', magazine.collection);
    }

    if (magazine.issue_number !== null && magazine.issue_number !== undefined) {
      formData.append('issue_number', magazine.issue_number.toString());
    }

    if (magazine.description) {
      formData.append('description', magazine.description);
    }

    formData.append('file', magazine.file);

    return this.http.post<MagazineResponse>(this.apiUrl, formData);
  }

  /**
   * Update magazine metadata
   */
  updateMagazine(id: number, magazine: MagazineUpdate): Observable<MagazineResponse> {
    return this.http.put<MagazineResponse>(`${this.apiUrl}/${id}`, magazine);
  }

  /**
   * Delete a magazine
   */
  deleteMagazine(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  /**
   * Download magazine PDF
   */
  downloadMagazine(id: number, title: string): void {
    this.getMagazineFileBlob(id).subscribe({
      next: (blob) => {
        downloadBlob(blob, `${title}.pdf`);
      },
      error: (error) => {
        console.error('Error downloading magazine:', error);
      }
    });
  }
}
