import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, catchError, of } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  EntityViewConfigResponse,
  EntityViewConfigUpdate,
  EntityViewConfigBulkUpdate,
  EntityViewConfigListResponse,
  ViewConfigItem
} from '../models/user.model';

export interface ViewMenuItem {
  routeLink: string;
  icon: string;
  label: string;
}

@Injectable({
  providedIn: 'root'
})
export class ViewConfigService {
  private apiUrl = `${environment.apiUrl}/view-configs`;

  // Signal para las configuraciones de vistas actuales
  private _viewConfigs = signal<EntityViewConfigResponse[]>([]);
  private _currentEntityId = signal<number | null>(null);
  private _statisticsEnabled = signal(false);
  statisticsEnabled = this._statisticsEnabled.asReadonly();

  // Computed para menú de navegación
  enabledViews = computed(() =>
    this._viewConfigs()
      .filter(v => v.is_enabled)
      .sort((a, b) => a.display_order - b.display_order)
  );

  allViews = computed(() =>
    this._viewConfigs()
      .sort((a, b) => a.display_order - b.display_order)
  );

  // Mapeo de view_name a rutas (sin slash inicial para rutas relativas)
  private readonly routeMap: Record<string, string> = {
    'dashboard': 'dashboard',
    'member_stats': 'member-stats',
    'users': 'directory',
    'entities': 'entities',
    'roles': 'roles',
    'activities': 'activities',
    'communications': 'blog',  // El blog es la vista pública de communications
    'magazines': 'magazines',
    'resources': 'resources',
    'chat': 'chat',
    'shop': 'shop',
    'fees': 'fees',
    'payments': 'payments',
    'settings': 'settings',
  };

  // Iconos por defecto
  private readonly defaultIcons: Record<string, string> = {
    'dashboard': 'dashboard',
    'member_stats': 'insights',
    'users': 'people',
    'entities': 'business',
    'roles': 'admin_panel_settings',
    'activities': 'event',
    'communications': 'newspaper',
    'magazines': 'menu_book',
    'resources': 'school',
    'chat': 'chat',
    'shop': 'store',
    'fees': 'payments',
    'payments': 'account_balance',
    'settings': 'settings',
  };

  constructor(private http: HttpClient) {}

  /** Statistics is globally enabled at Superentity, not per current membership. */
  loadStatisticsAvailability(): Observable<{ is_enabled: boolean }> {
    return this.http.get<{ is_enabled: boolean }>(
      `${this.apiUrl}/member-stats/availability`
    ).pipe(
      tap(response => this._statisticsEnabled.set(response.is_enabled)),
      catchError(() => {
        this._statisticsEnabled.set(false);
        return of({is_enabled: false});
      })
    );
  }

  /**
   * Obtener todas las configuraciones de vistas para una entidad
   */
  getEntityViewConfigs(entityId: number): Observable<EntityViewConfigListResponse> {
    return this.http.get<EntityViewConfigListResponse>(`${this.apiUrl}/entity/${entityId}`);
  }

  /**
   * Obtener solo las vistas habilitadas para una entidad
   */
  getEnabledViews(entityId: number): Observable<EntityViewConfigResponse[]> {
    return this.http.get<EntityViewConfigResponse[]>(`${this.apiUrl}/entity/${entityId}/enabled`);
  }

  /**
   * Actualizar configuración de una vista específica
   */
  updateViewConfig(
    entityId: number,
    viewName: string,
    config: EntityViewConfigUpdate
  ): Observable<EntityViewConfigResponse> {
    return this.http.put<EntityViewConfigResponse>(
      `${this.apiUrl}/entity/${entityId}/view/${viewName}`,
      config
    ).pipe(
      tap(updated => {
        if (viewName === 'member_stats') {
          this._statisticsEnabled.set(updated.is_enabled);
        }
      })
    );
  }

  /**
   * Actualizar múltiples configuraciones de vistas a la vez
   */
  bulkUpdateViewConfigs(
    entityId: number,
    configs: EntityViewConfigBulkUpdate
  ): Observable<EntityViewConfigListResponse> {
    return this.http.put<EntityViewConfigListResponse>(
      `${this.apiUrl}/entity/${entityId}/bulk`,
      configs
    ).pipe(
      tap(response => {
        this._viewConfigs.set(response.configs);
      })
    );
  }

  /**
   * Resetear configuraciones a valores por defecto
   */
  resetViewConfigs(entityId: number): Observable<EntityViewConfigListResponse> {
    return this.http.post<EntityViewConfigListResponse>(
      `${this.apiUrl}/entity/${entityId}/reset`,
      {}
    ).pipe(
      tap(response => {
        this._viewConfigs.set(response.configs);
      })
    );
  }

  /**
   * Cargar y cachear configuraciones de vistas para una entidad
   */
  loadViewConfigs(entityId: number): Observable<EntityViewConfigListResponse> {
    this._currentEntityId.set(entityId);
    return this.getEntityViewConfigs(entityId).pipe(
      tap(response => {
        this._viewConfigs.set(response.configs);
      }),
      catchError(error => {
        console.error('Error loading view configs:', error);
        this._viewConfigs.set([]);
        return of({ entity_id: entityId, configs: [] });
      })
    );
  }

  /**
   * Convertir configuraciones a items de menú para el sidebar
   */
  getMenuItems(): ViewMenuItem[] {
    return this.enabledViews().map(config => ({
      routeLink: this.routeMap[config.view_name] || config.view_name,
      icon: config.icon || this.defaultIcons[config.view_name] || 'article',
      label: config.display_name
    }));
  }

  /**
   * Verificar si una vista específica está habilitada
   */
  isViewEnabled(viewName: string): boolean {
    const config = this._viewConfigs().find(c => c.view_name === viewName);
    return config?.is_enabled ?? false;
  }

  /**
   * Obtener el nombre de display de una vista
   */
  getViewDisplayName(viewName: string): string {
    const config = this._viewConfigs().find(c => c.view_name === viewName);
    return config?.display_name ?? viewName;
  }

  /**
   * Obtener la ruta para una vista
   */
  getViewRoute(viewName: string): string {
    return this.routeMap[viewName] || viewName;
  }

  /**
   * Limpiar configuraciones (para logout)
   */
  clearConfigs(): void {
    this._statisticsEnabled.set(false);
    this._viewConfigs.set([]);
    this._currentEntityId.set(null);
  }
}
