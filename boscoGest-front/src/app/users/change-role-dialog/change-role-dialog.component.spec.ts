import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { of, throwError } from 'rxjs';

import {
  ChangeRoleDialogComponent,
  ChangeRoleDialogData,
} from './change-role-dialog.component';
import { EntitiesService } from '../../entities/entities.service';
import { MembershipsService } from '../memberships.service';
import { provideAppTesting } from '../../testing/test-providers';

describe('ChangeRoleDialogComponent', () => {
  let component: ChangeRoleDialogComponent;
  let fixture: ComponentFixture<ChangeRoleDialogComponent>;
  let entities: jasmine.SpyObj<EntitiesService>;
  let memberships: jasmine.SpyObj<MembershipsService>;
  let dialogRef: jasmine.SpyObj<MatDialogRef<ChangeRoleDialogComponent>>;

  const data: ChangeRoleDialogData = {
    membershipId: 5,
    entityId: 10,
    entityName: 'Cádiz',
    currentRoleName: 'socio',
    userName: 'Lucía Fernández',
  };

  const ROLES = [
    { id: 1, name: 'socio' },
    { id: 2, name: 'admin' },
  ];

  function crear(roles: unknown = ROLES) {
    entities.getEntityRoles.and.returnValue(of(roles) as never);
    fixture = TestBed.createComponent(ChangeRoleDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  beforeEach(() => {
    entities = jasmine.createSpyObj<EntitiesService>('EntitiesService', ['getEntityRoles']);
    memberships = jasmine.createSpyObj<MembershipsService>('MembershipsService', [
      'updateMembership',
    ]);
    dialogRef = jasmine.createSpyObj<MatDialogRef<ChangeRoleDialogComponent>>(
      'MatDialogRef',
      ['close'],
    );

    TestBed.configureTestingModule({
      imports: [ChangeRoleDialogComponent],
      providers: [
        provideAppTesting(),
        { provide: EntitiesService, useValue: entities },
        { provide: MembershipsService, useValue: memberships },
        { provide: MAT_DIALOG_DATA, useValue: data },
      ],
    }).overrideProvider(MatDialogRef, { useValue: dialogRef });
  });

  it('should create', () => {
    crear();
    expect(component).toBeTruthy();
  });

  it('pide los roles de esa asociación, no el catálogo global', () => {
    crear();
    // Cada asociación tiene los suyos; ofrecer uno ajeno daría error del
    // servidor después de haberlo elegido.
    expect(entities.getEntityRoles).toHaveBeenCalledWith(10);
  });

  it('parte del rol actual preseleccionado', () => {
    crear();
    expect(component.selectedRoleId()).toBe(1);
  });

  it('no deja guardar si no se ha cambiado nada', () => {
    crear();
    expect(component.sinCambios).toBeTrue();

    component.onSave();
    expect(memberships.updateMembership).not.toHaveBeenCalled();
  });

  it('guarda el rol nuevo y cierra con true', () => {
    crear();
    memberships.updateMembership.and.returnValue(of({}) as never);

    component.selectedRoleId.set(2);
    component.onSave();

    expect(memberships.updateMembership).toHaveBeenCalledWith(5, { role_id: 2 });
    expect(dialogRef.close).toHaveBeenCalledWith(true);
  });

  it('explica un 403 en vez de cerrarse sin más', () => {
    crear();
    memberships.updateMembership.and.returnValue(
      throwError(() => new HttpErrorResponse({ status: 403 })) as never,
    );

    component.selectedRoleId.set(2);
    component.onSave();

    expect(component.errorMessage()).toBe(
      'No tienes permiso para cambiar roles en esta asociación.',
    );
    expect(dialogRef.close).not.toHaveBeenCalled();
  });

  it('avisa si no se pueden cargar los roles', () => {
    entities.getEntityRoles.and.returnValue(throwError(() => new Error('red')) as never);
    fixture = TestBed.createComponent(ChangeRoleDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.errorMessage()).toContain('No se han podido cargar los roles');
    expect(component.loading()).toBeFalse();
  });

  it('cancelar cierra con false y no llama al servidor', () => {
    crear();
    component.onCancel();

    expect(dialogRef.close).toHaveBeenCalledWith(false);
    expect(memberships.updateMembership).not.toHaveBeenCalled();
  });
});
