import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, forkJoin, map } from 'rxjs';
import { environment } from '../../environments/environment';
import { EntityResponse, EntityCreate, EntityUpdate, EntityDetails, MembershipDetails, EntityDeletionImpact } from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class EntitiesService {
  private apiUrl = `${environment.apiUrl}/entities`;

  constructor(private http: HttpClient) {}

  getEntities(skip: number = 0, limit: number = 100): Observable<EntityResponse[]> {
    return this.http.get<EntityResponse[]>(this.apiUrl, {
      params: { skip: skip.toString(), limit: limit.toString() }
    });
  }

  /** Only the 4th-level associations; never confederations/federations. */
  getLocalAssociations(): Observable<EntityResponse[]> {
    return this.http.get<EntityResponse[]>(`${this.apiUrl}/associations`);
  }

  /** Entities in the authenticated user's visibility scope. */
  getAccessibleLocalAssociations(): Observable<EntityResponse[]> {
    return this.http.get<EntityResponse[]>(`${this.apiUrl}/accessible`).pipe(
      map(entities => entities.filter(entity => entity.level === 4))
    );
  }

  getEntity(entityId: number): Observable<EntityResponse> {
    return this.http.get<EntityResponse>(`${this.apiUrl}/${entityId}`);
  }

  getEntityDetails(entityId: number): Observable<EntityDetails> {
    return forkJoin({
      entity: this.http.get<EntityResponse>(`${this.apiUrl}/${entityId}`),
      memberships: this.http.get<MembershipDetails[]>(`${environment.apiUrl}/memberships`)
    }).pipe(
      map(({ entity, memberships }) => ({
        id: entity.id,
        name: entity.name,
        level: entity.level,
        parent_id: entity.parent_id,
        created_at: entity.created_at,
        parent: entity.parent || null,
        memberships: memberships.filter(m => m.entity_id === entityId)
      }))
    );
  }

  createEntity(entity: EntityCreate): Observable<EntityResponse> {
    return this.http.post<EntityResponse>(this.apiUrl, entity);
  }

  updateEntity(entityId: number, entity: EntityUpdate): Observable<EntityResponse> {
    return this.http.put<EntityResponse>(`${this.apiUrl}/${entityId}`, entity);
  }

  deleteEntity(entityId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${entityId}`);
  }

  /**
   * What removing this association would affect. Asked before deleting so the
   * warning arrives beforehand instead of the result arriving afterwards.
   */
  getDeletionImpact(entityId: number): Observable<EntityDeletionImpact> {
    return this.http.get<EntityDeletionImpact>(
      `${this.apiUrl}/${entityId}/deletion-impact`
    );
  }

  getAdminEntities(skip: number = 0, limit: number = 100): Observable<EntityResponse[]> {
    return this.http.get<EntityResponse[]>(`${this.apiUrl}/admin`, {
      params: { skip: skip.toString(), limit: limit.toString() }
    });
  }

  getEntityRoles(entityId: number): Observable<import('../models/user.model').RoleResponse[]> {
    return this.http.get<import('../models/user.model').RoleResponse[]>(`${this.apiUrl}/${entityId}/roles`);
  }

  getMembershipManageableEntities(skip: number = 0, limit: number = 100): Observable<EntityResponse[]> {
    return this.http.get<EntityResponse[]>(`${this.apiUrl}/membership-manageable`, {
      params: { skip: skip.toString(), limit: limit.toString() }
    });
  }
}
