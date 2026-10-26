import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

import { ConfirmDialogComponent, ConfirmDialogData } from './confirm-dialog.component';
import { provideAppTesting } from '../testing/test-providers';

describe('ConfirmDialogComponent', () => {
  let component: ConfirmDialogComponent;
  let fixture: ComponentFixture<ConfirmDialogComponent>;
  let dialogRef: jasmine.SpyObj<MatDialogRef<ConfirmDialogComponent>>;

  // Un diálogo no se instancia suelto: Material le inyecta la referencia y los
  // datos que recibe al abrirse, y sin ellas el componente ni se construye.
  const data: ConfirmDialogData = {
    title: 'Eliminar rol',
    message: '¿Seguro que quieres eliminar el rol?',
  };

  beforeEach(async () => {
    dialogRef = jasmine.createSpyObj<MatDialogRef<ConfirmDialogComponent>>(
      'MatDialogRef',
      ['close'],
    );

    await TestBed.configureTestingModule({
      imports: [ConfirmDialogComponent],
      providers: [
        provideAppTesting(),
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: MAT_DIALOG_DATA, useValue: data },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ConfirmDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('rellena los textos que no vengan en los datos', () => {
    expect(component.data.variant).toBe('confirm');
    expect(component.data.confirmText).toBe('Confirmar');
    expect(component.data.cancelText).toBe('Cancelar');
  });

  it('cierra con true al confirmar', () => {
    component.onConfirm();
    expect(dialogRef.close).toHaveBeenCalledWith(true);
  });
});
