import { Injectable, inject } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Observable, of, switchMap } from 'rxjs';
import { EntitiesService } from './entities.service';
import { ConfirmDialogComponent } from '../confirm-dialog/confirm-dialog.component';
import { EntityResponse, EntityDeletionImpact } from '../models/user.model';

/**
 * The one place that decides whether an association can be removed and what the
 * person is told before it happens. Shared by the list and the detail screen so
 * both behave the same.
 *
 * Two rules, and they differ on purpose:
 *
 *  - Associations underneath block the deletion outright. Removing the parent
 *    would leave them active with nowhere to hang from, still inheriting
 *    permissions through something that no longer exists. There is no safe way
 *    to interpret the request, so we explain and stop.
 *  - Members do not block it, but they lose their membership along with the
 *    association, so we say how many before asking.
 */
@Injectable({ providedIn: 'root' })
export class EntityDeletionService {
  private dialog = inject(MatDialog);
  private entitiesService = inject(EntitiesService);

  /**
   * Emits true only when the association was actually removed — false when it
   * was refused, cancelled, or the check itself failed.
   */
  confirmAndDelete(entity: EntityResponse | { id: number; name: string }): Observable<boolean> {
    return this.entitiesService.getDeletionImpact(entity.id).pipe(
      switchMap((impact) => {
        if (!impact.can_delete) {
          this.explainRefusal(entity.name, impact);
          return of(false);
        }
        return this.askForConfirmation(entity.name, impact).pipe(
          switchMap((confirmed) =>
            confirmed
              ? this.entitiesService.deleteEntity(entity.id).pipe(switchMap(() => of(true)))
              : of(false)
          )
        );
      })
    );
  }

  private explainRefusal(name: string, impact: EntityDeletionImpact): void {
    const plural = impact.child_count === 1 ? '' : 'es';
    const listed = impact.child_names;
    const remainder = impact.child_count - listed.length;

    this.dialog.open(ConfirmDialogComponent, {
      width: '32rem',
      maxWidth: '92vw',
      autoFocus: false,
      data: {
        variant: 'info',
        title: 'No se puede eliminar',
        message:
          `«${name}» tiene ${impact.child_count} asociaci${plural === '' ? 'ón' : 'ones'} por debajo. ` +
          'Si la elimináramos, quedarían activas sin nadie por encima. ' +
          'Muévelas a otra asociación o elimínalas primero.',
        details: remainder > 0 ? [...listed, `y ${remainder} más`] : listed,
        cancelText: 'Entendido',
      },
    });
  }

  private askForConfirmation(
    name: string,
    impact: EntityDeletionImpact
  ): Observable<boolean> {
    const members = impact.member_count;
    const message =
      members > 0
        ? `Se eliminará «${name}» y ${members === 1 ? 'su único socio perderá' : `sus ${members} socios perderán`} ` +
          'la membresía en ella. Las cuentas de usuario se conservan, junto con sus membresías en otras asociaciones.'
        : `Se eliminará «${name}». No tiene socios dados de alta.`;

    return this.dialog
      .open(ConfirmDialogComponent, {
        width: '32rem',
        maxWidth: '92vw',
        autoFocus: false,
        restoreFocus: false,
        data: {
          title: 'Eliminar asociación',
          message,
          confirmText: 'Eliminar',
          cancelText: 'Cancelar',
          danger: true,
        },
      })
      .afterClosed()
      .pipe(switchMap((result) => of(result === true)));
  }
}
