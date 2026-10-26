import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef } from '@angular/material/dialog';

import { FirstTimePasswordDialogComponent } from './first-time-password-dialog.component';
import { provideAppTesting } from '../testing/test-providers';

describe('FirstTimePasswordDialogComponent', () => {
  let component: FirstTimePasswordDialogComponent;
  let fixture: ComponentFixture<FirstTimePasswordDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FirstTimePasswordDialogComponent],
      providers: [
        provideAppTesting(),
        // Material la inyecta al abrir el diálogo; suelto, el componente no se
        // construye sin ella.
        { provide: MatDialogRef, useValue: jasmine.createSpyObj('MatDialogRef', ['close']) },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(FirstTimePasswordDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
