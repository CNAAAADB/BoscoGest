import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, catchError, of } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  EntityBrandingResponse,
  EntityBrandingCreate,
  EntityBrandingUpdate,
  EntityBrandingWithEntity
} from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class BrandingService {
  private apiUrl = `${environment.apiUrl}/branding`;

  // Signal para el branding actual
  private _currentBranding = signal<EntityBrandingResponse | null>(null);

  // Computed para valores derivados
  currentBranding = computed(() => this._currentBranding());

  // Colores por defecto
  readonly defaultColors = {
    primary: '#1976d2',
    secondary: '#424242',
    accent: '#ff4081'
  };

  constructor(private http: HttpClient) {}

  /**
   * Obtener branding de una entidad específica
   */
  getEntityBranding(entityId: number): Observable<EntityBrandingResponse> {
    return this.http.get<EntityBrandingResponse>(`${this.apiUrl}/entity/${entityId}`);
  }

  /**
   * Obtener branding por subdominio (público, para carga inicial)
   */
  getBrandingBySubdomain(subdomain: string): Observable<EntityBrandingWithEntity> {
    return this.http.get<EntityBrandingWithEntity>(`${this.apiUrl}/subdomain/${subdomain}`);
  }

  /**
   * Crear configuración de branding para una entidad
   */
  createBranding(branding: EntityBrandingCreate): Observable<EntityBrandingResponse> {
    return this.http.post<EntityBrandingResponse>(this.apiUrl, branding);
  }

  /**
   * Actualizar branding de una entidad
   */
  updateBranding(entityId: number, branding: EntityBrandingUpdate): Observable<EntityBrandingResponse> {
    return this.http.put<EntityBrandingResponse>(`${this.apiUrl}/entity/${entityId}`, branding);
  }

  /**
   * Subir logo para una entidad
   */
  uploadLogo(entityId: number, file: File): Observable<EntityBrandingResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<EntityBrandingResponse>(`${this.apiUrl}/entity/${entityId}/logo`, formData);
  }

  /**
   * Eliminar configuración de branding (resetear a valores por defecto)
   */
  deleteBranding(entityId: number): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.apiUrl}/entity/${entityId}`);
  }

  /**
   * Cargar y aplicar branding de una entidad
   */
  loadAndApplyBranding(entityId: number): Observable<EntityBrandingResponse | null> {
    return this.getEntityBranding(entityId).pipe(
      tap(branding => {
        this._currentBranding.set(branding);
        this.applyBrandingToDOM(branding);
      }),
      catchError(error => {
        // Si no hay branding configurado, usar valores por defecto
        if (error.status === 404) {
          this._currentBranding.set(null);
          this.resetBrandingToDefault();
        }
        return of(null);
      })
    );
  }

  /**
   * Aplicar colores de branding al DOM usando CSS custom properties
   */
  applyBrandingToDOM(branding: EntityBrandingResponse | null): void {
    const root = document.documentElement;

    if (branding) {
      root.style.setProperty('--primary-color', branding.primary_color);
      root.style.setProperty('--secondary-color', branding.secondary_color);
      root.style.setProperty('--accent-color', branding.accent_color);

      // Calcular colores derivados (más claros/oscuros)
      root.style.setProperty('--primary-light', this.lightenColor(branding.primary_color, 20));
      root.style.setProperty('--primary-dark', this.darkenColor(branding.primary_color, 20));
    } else {
      this.resetBrandingToDefault();
    }
  }

  /**
   * Resetear branding a valores por defecto
   */
  resetBrandingToDefault(): void {
    const root = document.documentElement;
    root.style.setProperty('--primary-color', this.defaultColors.primary);
    root.style.setProperty('--secondary-color', this.defaultColors.secondary);
    root.style.setProperty('--accent-color', this.defaultColors.accent);
    root.style.setProperty('--primary-light', this.lightenColor(this.defaultColors.primary, 20));
    root.style.setProperty('--primary-dark', this.darkenColor(this.defaultColors.primary, 20));
  }

  /**
   * Aclarar un color hex
   */
  private lightenColor(hex: string, percent: number): string {
    const num = parseInt(hex.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = (num >> 16) + amt;
    const G = (num >> 8 & 0x00FF) + amt;
    const B = (num & 0x0000FF) + amt;
    return '#' + (
      0x1000000 +
      (R < 255 ? (R < 1 ? 0 : R) : 255) * 0x10000 +
      (G < 255 ? (G < 1 ? 0 : G) : 255) * 0x100 +
      (B < 255 ? (B < 1 ? 0 : B) : 255)
    ).toString(16).slice(1);
  }

  /**
   * Oscurecer un color hex
   */
  private darkenColor(hex: string, percent: number): string {
    const num = parseInt(hex.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = (num >> 16) - amt;
    const G = (num >> 8 & 0x00FF) - amt;
    const B = (num & 0x0000FF) - amt;
    return '#' + (
      0x1000000 +
      (R > 0 ? R : 0) * 0x10000 +
      (G > 0 ? G : 0) * 0x100 +
      (B > 0 ? B : 0)
    ).toString(16).slice(1);
  }

  /**
   * Validar formato de color hex
   */
  isValidHexColor(color: string): boolean {
    return /^#[0-9A-Fa-f]{6}$/.test(color);
  }
}
