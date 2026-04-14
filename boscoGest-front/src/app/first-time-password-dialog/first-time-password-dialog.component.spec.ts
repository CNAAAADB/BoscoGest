import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FirstTimePasswordDialogComponent } from './first-time-password-dialog.component';

describe('FirstTimePasswordDialogComponent', () => {
  let component: FirstTimePasswordDialogComponent;
  let fixture: ComponentFixture<FirstTimePasswordDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FirstTimePasswordDialogComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(FirstTimePasswordDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
